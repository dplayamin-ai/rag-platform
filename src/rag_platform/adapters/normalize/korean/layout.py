r"""N2 `linebreaks` 단계 — 라틴 분철 결합과 줄바꿈 병합(하이픈·개행을 원문 좌표 `Edit`으로 기록).

역할: 페이지 포맷(`source_kind ≠ flow`)의 흐름 편집으로 잘린 단어를 되돌린다 — 줄 끝 라틴 하이픈
(`word-\nword`)은 하이픈과 개행을 함께 지워 붙이고, 한글 음절이 줄바꿈으로 갈라진 경우(`음절\n음절`)는
개행만 지워 붙이며, 그 외 문단 내부 개행은 공백으로 접는다(동일 길이라 `unicode.Edit`을 만들지 않고
`working` 버퍼에 직접 쓴다 — 04-pipelines/09 §4 "동일 길이 치환"). `enabled=False`(기본값, 계약 04 I-8
개정 전제·미해결 이슈 1)면 아무 것도 하지 않는다.
설계 근거: 04-pipelines/09 §3.2 N2(하이픈 결합·줄바꿈 병합 규칙, `korean_join=analyzer` 훅)·§2 체인
표(N2 대상 블록 = `source_kind≠flow`이고 `type∈{paragraph,list_item,heading,caption,footnote}`, 옵션
`flow`+`source=converted`)·§4(한글 결합 예시 L2).
구성: `merge_linebreaks(text, *, enabled, korean_join=None)` — `(working, edits, stats)`.
불변식·주의: 대상 블록 판정(어떤 블록에 이 함수를 부를지)은 `stage.py`의 책임이다 — 이 함수 자체는
어떤 텍스트에도 적용 가능한 순수 함수. `korean_join`은 한글 줄바꿈 결합을 승인/거부하는 콜러블
(`ctx.analyzer.normalize`)이며 미제공 시 항상 결합(`""`)한다.
검증 계층: 1층(여기서 검증) — `tests/adapters/normalize/test_normalize.py`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rag_platform.adapters.normalize.korean.unicode import Edit

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["merge_linebreaks"]

_HANGUL_SYLLABLE_LO, _HANGUL_SYLLABLE_HI = 0xAC00, 0xD7A3


def _is_hangul_syllable(ch: str) -> bool:
    return bool(ch) and _HANGUL_SYLLABLE_LO <= ord(ch) <= _HANGUL_SYLLABLE_HI


def _is_latin_letter(ch: str) -> bool:
    return bool(ch) and ch.isascii() and ch.isalpha()


def merge_linebreaks(
    text: str,
    *,
    enabled: bool,
    korean_join: Callable[[str], str] | None = None,
) -> tuple[str, list[Edit], dict[str, int]]:
    """라틴 분철 결합·한글 줄바꿈 결합·일반 개행 공백 치환. `enabled=False`면 무변화."""
    stats = {"dehyphenated": 0, "linebreaks_merged": 0}
    if not enabled:
        return text, [], stats
    chars = list(text)
    n = len(chars)
    edits: list[Edit] = []
    i = 0
    while i < n:
        ch = chars[i]
        if (
            ch == "-"
            and _is_latin_letter(chars[i - 1] if i > 0 else "")
            and i + 2 < n
            and chars[i + 1] == "\n"
            and _is_latin_letter(chars[i + 2])
        ):
            edits.append(Edit(i, 2, ""))
            stats["dehyphenated"] += 1
            i += 2
            continue
        if ch == "\n":
            prev_ch = chars[i - 1] if i > 0 else ""
            next_ch = chars[i + 1] if i + 1 < n else ""
            if _is_hangul_syllable(prev_ch) and _is_hangul_syllable(next_ch):
                joined_word = prev_ch + next_ch
                approved = korean_join is None or korean_join(joined_word) == joined_word
                if approved:
                    edits.append(Edit(i, 1, ""))
                    stats["linebreaks_merged"] += 1
                    i += 1
                    continue
            chars[i] = " "  # 동일 길이 치환 — offset_map 구간을 쪼개지 않는다(§4).
            stats["linebreaks_merged"] += 1
        i += 1
    return "".join(chars), edits, stats
