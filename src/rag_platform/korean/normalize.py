"""질의 정규화·언어 감지·형태소 키워드 추출의 순수 구현(N1 규칙 경로, 계약 아님).

역할: 04-pipelines/14 §1.1 `normalize_ko` — 원 질의를 표시 뷰(`normalized_query`, NFC)와 렉시컬 뷰
(형태소·필터 추출용, NFKC + 기호 통일)로 나누고, 문자 스크립트 비율로 `lang`을 판정하고,
`lexical_terms[]`(`NNG`/`NNP`/`SL`/`SN`/`USER_DICT`)를 뽑는다. `adapters/query/korean_normalize.py`
(Stage 5멤버 `KoreanNormalizeTransformer` 래퍼)와 `retrieval/planner.py`(규칙 경로 `plan()`)가 공유해
`korean`(L1, 바이블 §12) 층에 둔다 — `retrieval`·`adapters`는 독립 형제 계층이라 서로 직접 import할 수
없다(F4 배치 검증: `retrieval.planner` → `adapters.query.korean_normalize` 위반 해소).
설계 근거: 04-pipelines/14 §2(정규화)·§6(키워드), ADR-0021(Kiwi 승격·mecab-ko 임시); 계약
`query_plan.LexicalTerm`. `clean_unicode`/`apply_edits`/`fold_lexical`은 `korean/unicode.py`(F1 배치
산출물)를 그대로 재사용한다(같은 U1~U5 규칙, 04-pipelines/09 §3.1).
구성: `normalize_query(raw_query, *, use_kiwi=None) -> NormalizeResult`; `detect_lang(text) -> str`;
`resolve_kiwi(*, use_kiwi) -> (kiwi_or_none, analyzer_id)` — `KoreanNormalizeTransformer.fingerprint()`도
재사용.
불변식·주의: 표시 뷰(NFC)와 렉시컬 뷰(NFKC)를 혼용하지 않는다(§2.1). 한자→한글 독음은 문서 자체가
정확도 미검증이라 DEFERRED. `kiwipiepy`는 선택 의존성 — 미설치 시 문자 클래스 폴백 토크나이저로
전환한다(`enricher.korean_keywords`와 같은 try/except 관례). `korean`(L1) 층은 `sdk`(같은 계층의
독립 형제, 바이블 §12)를 import할 수 없어 `NormalizeResult.dictionary_hash`는 이 함수가 채우지
않는다(항상 `""`) — `H("dict")`는 `sdk.hashing`을 가진 호출자(`retrieval.planner`/
`adapters.query.korean_normalize`)가 `dataclasses.replace`로 덮어쓴다.
검증 계층: 1층(여기서 검증) — `tests/retrieval/test_planner.py`. `kiwipiepy` 미설치가 기본 테스트 경로.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from rag_platform.contracts.query_plan import LexicalTerm
from rag_platform.korean.unicode import apply_edits, clean_unicode, fold_lexical

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["NormalizeResult", "detect_lang", "normalize_query", "resolve_kiwi"]

#: 공용 명사 불용어(04-pipelines/11 §5.1과 동일 초안 목록, 14 §6.3).
_STOPWORDS_COMMON = frozenset({"것", "등", "수", "때", "경우", "관련", "해당", "다음", "이상", "이하", "내용", "사항"})
#: 질의 전용 추가 불용어(§6.3) — 시기·방법·가능성을 묻는 질의 틀 어휘. "여부"·"이내"는 제외하지 않는다.
_STOPWORDS_QUERY_ONLY = frozenset({"이후", "이전", "최근", "방법", "가능"})
#: 의도·의문 불용어(§6.3) — 라우터 신호로만 쓰고 `lexical_terms`에는 넣지 않는다.
_STOPWORDS_INTENT = frozenset(
    {"며칠", "몇", "얼마", "어떤", "무슨", "비교", "차이", "정리", "요약", "설명", "알려", "안내"}
)
_ALL_STOPWORDS = _STOPWORDS_COMMON | _STOPWORDS_QUERY_ONLY | _STOPWORDS_INTENT
#: PII 마스킹 자리표시자(`<PERSON>` 등) — 후보에서 제외한다.
_MASK_TOKEN_RE = re.compile(r"^<[A-Z_]+>$")
#: 인사·감사 감탄 어간(§3.2 규칙 1 `chitchat` 어휘와 같은 목록) — 문장형("안녕하세요")도 내용 명사로
#: 세지 않도록 접두 일치로 걸러낸다(라우터의 "내용 명사 0개" 판정이 성립하려면 여기서 먼저 빠져야 한다).
_INTERJECTION_PREFIXES = ("안녕", "감사", "고맙", "고마", "반갑", "수고")
#: Kiwi가 직접 내는 태그 중 이 WP가 그대로 받는 것(§6.2 v1 태그 집합의 분석기 유래분).
_KIWI_DIRECT_TAGS = frozenset({"NNG", "NNP", "SL", "SN"})
#: 폴백 토크나이저의 후보 구간 — 숫자 연속, 라틴 연속, 한글 음절 연속(§2.1 표 문자 부류).
_TOKEN_RE = re.compile(r"[0-9]+(?:\.[0-9]+)*|[A-Za-z]+|[가-힣]+")
#: 조사 접미 후보(길이 내림차순으로 최장 일치를 먼저 시도) — 폴백 명사 근사(§6.1 규칙 4 대체).
_JOSA_SUFFIXES: tuple[str, ...] = tuple(
    sorted(
        {
            "에서부터",
            "이라고는",
            "까지는",
            "에게는",
            "이라도",
            "라서는",
            "이었다",
            "였다",
            "이나마",
            "은",
            "는",
            "이",
            "가",
            "을",
            "를",
            "의",
            "에",
            "와",
            "과",
            "도",
            "만",
            "께",
            "나",
            "로",
            "으로",
            "라도",
            "부터",
            "까지",
            "에게",
            "보다",
            "이나",
            "라서",
            "인데",
            "이라서",
            "한테",
            "마다",
            "조차",
            "마저",
            "밖에",
        },
        key=len,
        reverse=True,
    )
)
_MIN_TERM_CHARS = 2
_MAX_LEXICAL_TERMS = 128
#: 언어 감지 임계(§2.2 표). 한글 비율 ≥ 이면 `ko`, 그 다음 한자 비율 ≥ 이면 `zh`/`ja`.
_HANGUL_RATIO_THRESHOLD = 0.3
_HAN_RATIO_THRESHOLD = 0.5
#: 언어 감지 문자 스크립트 코드포인트 구간(§2.2) — 한글 음절·자모·호환자모 / 가나(히라·가타) / 한자.
_HANGUL_SYLLABLE_RANGE = (0xAC00, 0xD7A3)
_HANGUL_JAMO_RANGE = (0x1100, 0x11FF)
_HANGUL_COMPAT_JAMO_RANGE = (0x3130, 0x318F)
_KANA_RANGE = (0x3040, 0x30FF)
_HAN_RANGE = (0x4E00, 0x9FFF)
#: 기호 통일(§2.1 규칙 4, 렉시컬 뷰 전용) — 가운뎃점 계열 `·`, 물결 계열 `~`, 대시 계열 `-`. 왼쪽 키는
#: 질의문에 나타나는 실제 유니코드 기호라 자모·다양한 대시가 뒤섞여 RUF001("ambiguous character")이
#: 전부 걸린다 — 의도된 것이라 줄마다 억제한다.
_SYMBOL_MAP = str.maketrans(
    {
        "ㆍ": "·",
        "•": "·",
        "∼": "~",  # noqa: RUF001 - TILDE OPERATOR
        "～": "~",  # noqa: RUF001 - FULLWIDTH TILDE
        "–": "-",  # noqa: RUF001 - EN DASH
        "—": "-",
        "―": "-",
        "‐": "-",  # noqa: RUF001 - HYPHEN
        "‑": "-",  # noqa: RUF001 - NON-BREAKING HYPHEN
        "‒": "-",  # noqa: RUF001 - FIGURE DASH
    }
)
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class NormalizeResult:
    """`normalize_query()`의 결과 — `QueryPlan`에 그대로 옮겨지는 필드만 담는다(계약 아님)."""

    original_query: str
    normalized_query: str
    lexical_view: str
    lang: str
    lexical_terms: list[LexicalTerm]
    analyzer_id: str
    dictionary_hash: str


def _collapse_whitespace(text: str) -> str:
    """연속 공백·탭·줄바꿈을 공백 1개로 접고 양끝을 trim한다(§2.1 규칙 3)."""
    return _WHITESPACE_RE.sub(" ", text).strip()


def _display_view(raw_query: str) -> str:
    """N1 규칙(제어문자·NBSP·NFC)을 적용한 표시 뷰를 만든다(§2.1 규칙 1~3, 표시 뷰 열)."""
    working, edits, _stats = clean_unicode(raw_query)
    display_text, _offset_map = apply_edits(working, edits)
    return _collapse_whitespace(display_text)


def _lexical_view(display_text: str) -> str:
    """렉시컬 뷰(NFKC + 기호 통일 + 소문자화)를 만든다(§2.1 규칙 1·4·6, 렉시컬 뷰 열).

    한자→한글 독음(규칙 5)은 문서 자체가 "정확도 확인 필요(as of 2026-09)"라 명시해 이 WP는 구현하지
    않는다: `# DEFERRED: 한자→한글 독음 변환(§2.1 규칙 5) — kss `hanja2hangul` 정확도 미검증`.
    """
    folded = fold_lexical(display_text)
    unified = folded.translate(_SYMBOL_MAP).lower()
    return _collapse_whitespace(unified)


def detect_lang(text: str) -> str:
    """문자 스크립트 비율로 `lang`을 판정한다(§2.2 표, 초안 휴리스틱).

    공백·숫자·구두점은 비율 계산에서 제외한다. 혼용 질의(예 "RAG 파이프라인 설계")는 한글 비율이
    임계를 넘으면 `ko`로 처리하고 라틴 토큰은 `lexical_terms`에 `SL`로 남는다(§2.2 "혼용 질의").
    """
    hangul = han = kana = counted = 0
    for ch in text:
        if not ch.isalpha():
            continue
        counted += 1
        cp = ord(ch)
        if (
            _HANGUL_SYLLABLE_RANGE[0] <= cp <= _HANGUL_SYLLABLE_RANGE[1]
            or _HANGUL_JAMO_RANGE[0] <= cp <= _HANGUL_JAMO_RANGE[1]
            or _HANGUL_COMPAT_JAMO_RANGE[0] <= cp <= _HANGUL_COMPAT_JAMO_RANGE[1]
        ):
            hangul += 1
        elif _KANA_RANGE[0] <= cp <= _KANA_RANGE[1]:
            kana += 1
        elif _HAN_RANGE[0] <= cp <= _HAN_RANGE[1]:
            han += 1
    if counted == 0:
        return "ko"
    if hangul / counted >= _HANGUL_RATIO_THRESHOLD:
        return "ko"
    if han / counted >= _HAN_RATIO_THRESHOLD:
        return "ja" if kana > 0 else "zh"
    return "en"


def _strip_josa(token: str) -> str:
    """최장 일치 조사 접미를 하나 제거한다(폴백 명사 근사, 결과가 너무 짧으면 원형을 돌려준다)."""
    for suffix in _JOSA_SUFFIXES:
        if len(token) > len(suffix) + 1 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def _fallback_tokens(lexical_view: str) -> list[tuple[str, str]]:
    """`kiwipiepy` 미설치 폴백 — 문자 클래스 구간을 후보로 삼는다(근사치, WP-401 open issue)."""
    tokens: list[tuple[str, str]] = []
    for match in _TOKEN_RE.finditer(lexical_view):
        raw = match.group(0)
        if raw[0].isdigit():
            tokens.append((raw, "SN"))
        elif raw.isascii():
            tokens.append((raw, "SL"))
        else:
            tokens.append((_strip_josa(raw), "NNG"))
    return tokens


def resolve_kiwi(*, use_kiwi: bool | None) -> tuple[Any | None, str]:
    """`use_kiwi` 오버라이드 또는 자동 감지로 `kiwipiepy.Kiwi`를 만든다(`enricher.korean_keywords` 관례).

    `adapters/query/korean_normalize.py`의 `KoreanNormalizeTransformer.fingerprint()`도 이 함수를
    재사용한다(같은 `analyzer_id` 철자를 내야 한다).

    Returns:
        `(kiwi_instance_or_none, analyzer_id)` — `analyzer_id`는 실제 사용한 엔진(§6.1 철자).
    """
    if use_kiwi is False:
        return None, "regex-fallback:1:none"
    if use_kiwi is True:
        import kiwipiepy  # noqa: PLC0415 - 선택 의존성, 강제 사용 시 ImportError 그대로 전파

        return kiwipiepy.Kiwi(), f"kiwi:{kiwipiepy.__version__}:none"
    try:
        import kiwipiepy  # noqa: PLC0415 - 선택 의존성(B등급 LGPL), 미설치 시 폴백
    except ImportError:
        return None, "regex-fallback:1:none"
    return kiwipiepy.Kiwi(), f"kiwi:{kiwipiepy.__version__}:none"


def _kiwi_tokens(lexical_view: str, kiwi: Any) -> list[tuple[str, str]]:
    """Kiwi 형태소 열에서 `NNG`/`NNP`/`SL`/`SN`만 채택한다(`W_*`/`Z_*` 확장 매핑은 DEFERRED)."""
    tokens: list[tuple[str, str]] = []
    for token in kiwi.tokenize(lexical_view):
        if token.tag in _KIWI_DIRECT_TAGS:
            form = token.form.lower() if token.tag == "SL" else token.form
            tokens.append((form, token.tag))
    return tokens


def _filter_and_weight(pairs: Sequence[tuple[str, str]]) -> list[LexicalTerm]:
    """§6.1 규칙 3·5·7: 불용어·마스크 토큰 제거 후 `(term, tag)` 유일화, 가중 1.0, 등장 순 정렬."""
    order: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for raw_term, tag in pairs:
        term = raw_term.strip()
        if (
            len(term) < _MIN_TERM_CHARS
            or _MASK_TOKEN_RE.match(term)
            or term in _ALL_STOPWORDS
            or term.startswith(_INTERJECTION_PREFIXES)
        ):
            continue
        key = (term, tag)
        if key not in seen:
            seen.add(key)
            order.append(key)
    terms = [LexicalTerm(term=term, weight=1.0, tag=tag) for term, tag in order]
    if len(terms) > _MAX_LEXICAL_TERMS:
        terms = terms[:_MAX_LEXICAL_TERMS]
    return terms


def normalize_query(raw_query: str, *, use_kiwi: bool | None = None) -> NormalizeResult:
    """원 질의를 정규화하고 언어·형태소 키워드를 뽑는다(04-pipelines/14 §2·§6).

    Args:
        raw_query: `QueryRequest.query`(1..4,000 코드포인트, 원문 보존).
        use_kiwi: 테스트용 오버라이드. `None`(기본)이면 `kiwipiepy` 가용성 자동 감지.

    Returns:
        `NormalizeResult` — `normalized_query`(표시 뷰), `lexical_view`, `lang`, `lexical_terms`,
        `analyzer_id`, `dictionary_hash`(항상 `""` — 모듈 독스트링 참고, 호출자가 `H("dict")`로 채운다).
    """
    display_text = _display_view(raw_query)
    lexical_view = _lexical_view(display_text)
    lang = detect_lang(display_text)
    kiwi, analyzer_id = resolve_kiwi(use_kiwi=use_kiwi)
    candidates = _kiwi_tokens(lexical_view, kiwi) if kiwi is not None else _fallback_tokens(lexical_view)
    lexical_terms = _filter_and_weight(candidates)
    # H("dict", *sorted(entry 정규화 행))은 `sdk.hashing`이 필요해 이 계층에서 계산하지 않는다(위 불변식
    # 참고) — 이 WP는 사용자 사전을 배선하지 않아 어차피 빈 목록(§6.1 규칙 4 DEFERRED).
    return NormalizeResult(
        original_query=raw_query,
        normalized_query=display_text,
        lexical_view=lexical_view,
        lang=lang,
        lexical_terms=lexical_terms,
        analyzer_id=analyzer_id,
        dictionary_hash="",
    )
