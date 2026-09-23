"""규칙 기반 의도 분류·라우팅·전략 채택의 순수 구현(04-pipelines/14 §3, 계약 아님).

역할: 형태소 열(`lexical_terms`)과 원 질의 문자열만으로 내부 의도 라벨(§3.1 표 6종)을 매기고, 이를
`route`/`complexity`(§3.1)로 옮기고, `strategy_hint`를 컬렉션 능력 대조 없이(이 WP 읽기 예산 밖)
`hybrid`/`iterative`만 채택한다(§3.4). `adapters/query/rule_router.py`(Stage 5멤버
`RuleRouterTransformer` 래퍼)와 `retrieval/planner.py`(규칙 경로 `plan()`)가 공유해 `korean`(L1,
바이블 §12) 층에 둔다 — `retrieval`·`adapters`는 독립 형제 계층이라 서로 직접 import할 수 없다(F4
배치 검증: `retrieval.planner` → `adapters.query.rule_router` 위반 해소).
설계 근거: 04-pipelines/14 §3.1(의도→계약 매핑)·§3.2(규칙 라우터, "항상 실행")·§3.4(`strategy_hint`
채택 조건); 바이블 §5.7 `Route`/`Complexity`/`Strategy`/`DegradedComponent`/`DegradedReason`.
구성: `classify_intent(lexical_terms, raw_query, *, has_conversation) -> str`;
`route_for_intent(intent) -> (Route, Complexity)`; `adopt_strategy(strategy_hint) -> (Strategy,
degraded[])`; `is_explanatory(raw_query) -> bool`.
불변식·주의: 규칙은 형태소 태그와 소형 어휘 목록만 쓰고 외부 모델을 부르지 않는다(§3.2 "규칙 항상").
소형 분류기·LLM 라우터(§3.3)는 이 WP 범위 밖(DEFERRED, `budget.llm_calls_allowed=false`).
검증 계층: 1층(여기서 검증) — `tests/retrieval/test_planner.py`.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from rag_platform.contracts import common_types as ct

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rag_platform.contracts.query_plan import LexicalTerm

__all__ = ["adopt_strategy", "classify_intent", "is_explanatory", "route_for_intent"]

#: 내용 명사로 치는 태그(§3.2 규칙 1·4 "내용 명사(NNG·NNP·SL·USER_DICT)" — `SN`은 제외).
_CONTENT_NOUN_TAGS = frozenset({"NNG", "NNP", "SL", "USER_DICT"})
#: 규칙 1: 인사·감사·잡담 어휘(초안 목록).
_GREETING_WORDS = ("안녕", "감사", "고마", "반가", "수고", "ㅋㅋ", "ㅎㅎ")
#: 규칙 2: 지시어·접속어로 시작하거나 포함(후속 질문 신호).
_FOLLOW_UP_MARKERS = (
    "그럼",
    "그러면",
    "그건",
    "그것",
    "그거",
    "이것",
    "이건",
    "거기",
    "그 경우",
    "위에서",
    "앞서",
    "아까",
    "또",
    "그리고",
    "아니면",
    "근데",
)
#: 규칙 3: 비교·집계 표지.
_COMPARE_MARKERS = (
    "비교",
    "차이",
    "대비",
    "vs",
    "각각",
    "모두",
    "총",
    "합계",
    "건수",
    "추이",
    "연도별",
    "월별",
    "증감",
)
#: 규칙 3: 나열 접속(개체·연도를 잇는 표지).
_LISTING_CONNECTORS = ("및", ",", "~", "와", "과")
#: 규칙 4: 조회형 문서번호·법령 조항 패턴.
_ARTICLE_RE = re.compile(r"제\d+조(제\d+항)?")
_DOC_NUMBER_RE = re.compile(r"[가-힣]+-\d{4}-\d+")
#: 규칙 4·6: 질문형/명령형 종결(어느 쪽에도 걸리면 "종결어미 있음"으로 간주해 규칙 4를 배제).
_QUESTION_ENDINGS = ("나요", "까요", "습니까", "는지")
_IMPERATIVE_ENDINGS = ("해줘", "알려", "정리해", "찾아")
#: 규칙 5: 전반적 주제 요약 표지.
_GLOBAL_THEMATIC_MARKERS = ("전반", "전체", "주요", "개요", "요약")
#: 규칙 6: 의문사(자연어 질문 신호, 기본값이라 분류에는 안 쓰지만 `explanatory` 판정에 재사용).
_EXPLANATORY_WORDS = ("왜", "어떻게", "원리", "배경", "이유")
_MAX_CONTENT_NOUNS_FOR_KEYWORD_LOOKUP = 8
_CONTENT_NOUN_RATIO_FOR_KEYWORD_LOOKUP = 0.6
_MAX_CONTENT_NOUNS_FOR_FOLLOW_UP = 2
_MAX_CONTENT_NOUNS_FOR_GLOBAL_THEMATIC = 2
_MIN_YEAR_TOKENS_FOR_COMPARE = 2
_YEAR_RE = re.compile(r"\b\d{4}\b")

#: §3.1 표: 의도 → (`route`, `complexity`). `quality`가 `compare_aggregate`를 `multi`로 올리는 것은
#: 이 규칙 경로(LLM 없음)에는 적용하지 않는다(04-pipelines/14 §3.1 "→ `quality`: `multi`" 열).
_ROUTE_COMPLEXITY: dict[str, tuple[ct.Route, ct.Complexity]] = {
    "chitchat": (ct.Route.no_retrieval, ct.Complexity.no_retrieval),
    "keyword_lookup": (ct.Route.single, ct.Complexity.single_step),
    "natural_question": (ct.Route.single, ct.Complexity.single_step),
    "compare_aggregate": (ct.Route.single, ct.Complexity.single_step),
    "follow_up": (ct.Route.single, ct.Complexity.single_step),
    "global_thematic": (ct.Route.single, ct.Complexity.single_step),
}

#: §3.4 표: 채택하지 못한 `strategy_hint`가 요구하는 채널의 `DegradedComponent`.
_STRATEGY_HINT_COMPONENT: dict[ct.Strategy, ct.DegradedComponent] = {
    ct.Strategy.graph_local: ct.DegradedComponent.channel_graph,
    ct.Strategy.graph_global: ct.DegradedComponent.channel_graph,
    ct.Strategy.tree_collapsed: ct.DegradedComponent.channel_tree,
    ct.Strategy.visual_pages: ct.DegradedComponent.channel_visual,
}
#: 능력 대조 없이 항상 채택하는 힌트(§3.4: `hybrid`는 항상, `iterative`는 "에이전트 루프는 클라이언트
#: 측"이라 검색 전략 자체에는 영향이 없어 항상).
_ALWAYS_ADOPTED_STRATEGIES = frozenset({ct.Strategy.hybrid, ct.Strategy.iterative})


def _content_noun_count(lexical_terms: Sequence[LexicalTerm]) -> int:
    """`lexical_terms` 중 내용 명사 태그(`NNG`·`NNP`·`SL`·`USER_DICT`) 개수(§3.2 규칙 1·4)."""
    return sum(1 for term in lexical_terms if term.tag in _CONTENT_NOUN_TAGS)


_TRAILING_PUNCTUATION_RE = re.compile(r"[?!.,~]+$")


def _has_ending(query: str, endings: Sequence[str]) -> bool:
    """`query`가 `endings` 중 하나로 끝나는지(말미 구두점·공백 제거 후 접미 비교)."""
    stripped = _TRAILING_PUNCTUATION_RE.sub("", query.strip())
    return any(stripped.endswith(ending) for ending in endings)


def _looks_like_keyword_lookup(query: str, content_nouns: int, total_tokens: int) -> bool:
    """규칙 4 근사 — 정규식 패턴 또는 "종결어미 없음 + 짧고 명사 비율 높음"(§3.2)."""
    if _ARTICLE_RE.search(query) or _DOC_NUMBER_RE.search(query):
        return True
    if _has_ending(query, (*_QUESTION_ENDINGS, *_IMPERATIVE_ENDINGS)):
        return False
    if total_tokens == 0 or total_tokens > _MAX_CONTENT_NOUNS_FOR_KEYWORD_LOOKUP:
        return False
    return (content_nouns / total_tokens) >= _CONTENT_NOUN_RATIO_FOR_KEYWORD_LOOKUP


def _looks_like_compare_aggregate(query: str) -> bool:
    """규칙 3 근사 — 비교 표지 + (나열 접속 또는 4자리 연도 ≥ 2개, §3.2)."""
    if not any(marker in query for marker in _COMPARE_MARKERS):
        return False
    if any(connector in query for connector in _LISTING_CONNECTORS):
        return True
    return len(_YEAR_RE.findall(query)) >= _MIN_YEAR_TOKENS_FOR_COMPARE


def classify_intent(
    lexical_terms: Sequence[LexicalTerm],
    raw_query: str,
    *,
    has_conversation: bool,
) -> str:
    """§3.2 6우선순위 규칙으로 내부 의도 라벨을 매긴다(정규식·소형 어휘 목록만, 외부 모델 없음).

    Args:
        lexical_terms: `korean.normalize.normalize_query()`가 만든 형태소 키워드.
        raw_query: 정규화된 질의(라우팅 신호는 렉시컬 뷰가 아니라 표시 뷰 문자열에서도 찾는다 —
            §3.2의 지시어·표지 예시가 원문 형태이기 때문).
        has_conversation: `QueryRequest.conversation`이 있는지(규칙 2 전제 조건).

    Returns:
        내부 의도 라벨 문자열(계약 필드 아님, §3.1) — `chitchat`|`keyword_lookup`|
        `natural_question`|`compare_aggregate`|`follow_up`|`global_thematic`.
    """
    content_nouns = _content_noun_count(lexical_terms)
    total_tokens = len(lexical_terms)
    if content_nouns == 0 and any(word in raw_query for word in _GREETING_WORDS):
        return "chitchat"
    if has_conversation and (
        any(raw_query.startswith(marker) or marker in raw_query for marker in _FOLLOW_UP_MARKERS)
        or content_nouns <= _MAX_CONTENT_NOUNS_FOR_FOLLOW_UP
    ):
        return "follow_up"
    if _looks_like_compare_aggregate(raw_query):
        return "compare_aggregate"
    if _looks_like_keyword_lookup(raw_query, content_nouns, total_tokens):
        return "keyword_lookup"
    if any(marker in raw_query for marker in _GLOBAL_THEMATIC_MARKERS) and (
        content_nouns <= _MAX_CONTENT_NOUNS_FOR_GLOBAL_THEMATIC
    ):
        return "global_thematic"
    return "natural_question"


def is_explanatory(raw_query: str) -> bool:
    """§3.2 "의문사 어휘 중 왜·어떻게·원리·배경·이유" 부가 플래그(step-back 옵션 조건, 이 WP는 미사용)."""
    return any(word in raw_query for word in _EXPLANATORY_WORDS)


def route_for_intent(intent: str) -> tuple[ct.Route, ct.Complexity]:
    """§3.1 표대로 내부 의도를 `(route, complexity)`로 옮긴다.

    Raises:
        ValueError: `intent`가 §3.1 표의 6종 라벨 밖일 때.
    """
    mapped = _ROUTE_COMPLEXITY.get(intent)
    if mapped is None:
        msg = f"unknown intent {intent!r}; expected one of {sorted(_ROUTE_COMPLEXITY)}"
        raise ValueError(msg)
    return mapped


def adopt_strategy(strategy_hint: ct.Strategy | None) -> tuple[ct.Strategy, list[ct.DegradedEntry]]:
    """§3.4 표대로 `strategy_hint`를 채택하거나 `hybrid`로 되돌린다.

    이 WP는 `CollectionSpec`/`IndexBackendCapabilities` 능력 대조를 읽기 예산 밖에 두므로(WP-401
    open issue), `hybrid`·`iterative`(능력 대조가 필요 없는 두 값, §3.4)만 그대로 채택하고 그 외는
    항상 불채택 + `degraded{channel.*, capability_unsupported}`로 기록한다.
    """
    if strategy_hint is None or strategy_hint in _ALWAYS_ADOPTED_STRATEGIES:
        return strategy_hint or ct.Strategy.hybrid, []
    component = _STRATEGY_HINT_COMPONENT[strategy_hint]
    degraded_entry = ct.DegradedEntry(
        component=component,
        reason=ct.DegradedReason.capability_unsupported,
        detail=(
            f"strategy_hint={strategy_hint.value} requires collection capability data "
            "(CollectionSpec/IndexBackendCapabilities) not available to the rule-path planner (WP-401)"
        ),
    )
    return ct.Strategy.hybrid, [degraded_entry]
