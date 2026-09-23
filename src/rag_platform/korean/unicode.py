"""N1 `unicode` 단계 — 제어문자 제거·NBSP·NFC 합성과 원문 좌표 `offset_map` 생성 유틸리티.

역할: 블록 `text`(원문)를 `display_text`(NFC, 표시·인용 원문)로 편집하면서 그 편집을 04-pipelines/09
§4(원문 오프셋 매핑 유지 규칙)가 정한 세 연산(동일 길이 치환·삭제·불투명 치환)으로 기록한다. 동일 길이
치환(NBSP→공백, 같은 길이로 합성되는 NFC 클러스터)은 `offset_map` 구간을 쪼개지 않도록 `working` 버퍼에
직접 반영하고, 길이가 바뀌는 편집(삭제·길이가 다른 합성)만 `Edit`으로 기록해 `apply_edits`가 최종
`display_text`·`offset_map`을 조립한다. `fold_lexical`은 N11 렉시컬 뷰의 문자 단위 NFKC 폴딩(호환 자모
보존)만 이 WP 범위에서 담당한다. 문서·질의 양쪽(N1 파싱 정규화 + `query_transformer.korean_normalize`)이
공유해 `korean`(L1, 바이블 §12) 층에 둔다 — `retrieval`·`adapters`는 독립 형제 계층이라 서로 직접
import할 수 없다(F4 배치 검증: `retrieval.planner` → `adapters.query.korean_normalize` 위반 해소).
설계 근거: 04-pipelines/09 §3.1 N1(U1~U5 규칙표)·§4(연산 3종·`offset_map` 정규형·예시); 바이블 §5.4
`NormalizedBlock.offset_map`(`[display_start, original_start, length]`); 계약
`contracts/normalized_document`(`OffsetMapItem` 각 항목 `min_length=3`).
구성: `Edit` — 원문 좌표 구조적 편집(길이가 바뀌는 삭제·치환만); `apply_edits(original, edits)` —
`Edit` 목록을 `offset_map` 정규형으로 조립(끝은 항상 `[len(display), len(original), 0]` sentinel);
`clean_unicode(text)` — U1~U5 적용, `(working, edits, stats)` 반환; `fold_lexical(display_text)` —
호환 자모(U+3130~U+318F)는 그대로 두고 나머지만 문자 단위 NFKC.
불변식·주의: `Edit`은 항상 `len(replacement) != length`(동일 길이 변경은 `Edit`을 만들지 않는다). 겹치는
`Edit`은 `ValueError`(호출측이 `contract.violation`으로 격상). `apply_edits`는 순수 함수(부작용 없음).
검증 계층: 1층(여기서 검증) — `tests/adapters/normalize/test_normalize.py`.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["Edit", "apply_edits", "clean_unicode", "fold_lexical"]

#: 유지 대상 `Cc`(탭·LF). `CR`(U+000D)은 여기 없어 다른 `Cc`와 함께 삭제된다(U1 = U3의 특수 사례).
_CC_KEEP = frozenset({0x09, 0x0A})
#: NBSP(U4). 공백으로 치환(동일 길이 — `offset_map` 구간을 쪼개지 않는다).
_NBSP = 0xA0
#: 결합 연쇄 판정에 쓰는 유니코드 일반 범주(라틴 결합 발음 구별 부호).
_COMBINING_CATEGORIES = frozenset({"Mn", "Mc", "Me"})
#: 조합형 한글 자모(초성·중성·종성) 구간 — 뒤 문자가 이 구간이면 앞 문자와 한 클러스터로 묶는다.
_JAMO_LO, _JAMO_HI = 0x1100, 0x11FF
#: 호환 자모(U+3130~U+318F, "ㅋㅋ" 류) — NFKC로 조합형 자모(U+1100대)로 바뀌지 않도록 보존한다.
_COMPAT_JAMO_LO, _COMPAT_JAMO_HI = 0x3130, 0x318F


@dataclass(frozen=True)
class Edit:
    """원문 좌표 구조적 편집 하나: `original[start:start+length]` → `replacement`.

    `length != len(replacement)`인 경우만 만든다(동일 길이 변경은 `working` 버퍼에 직접 써서 `offset_map`
    구간을 쪼개지 않는다, 04-pipelines/09 §4 "동일 길이 치환" 행). `replacement == ""`이면 삭제(M6 경계
    마커), 아니면 불투명 치환(M5)이다.
    """

    start: int
    length: int
    replacement: str


def apply_edits(original: str, edits: Sequence[Edit]) -> tuple[str, list[list[int]]]:
    """`edits`(원문 좌표, 서로 겹치지 않음)를 `original`에 적용해 `(display_text, offset_map)`을 만든다.

    04-pipelines/09 §4 정규형을 그대로 구현한다: 삭제가 이어지면 마커 하나로 접고(다음 실제 구간의
    `original_start`가 삭제량을 말해준다), 문자열 끝에서 끝나는 삭제는 전용 마커 없이 후행 sentinel
    (`[len(display), len(original), 0]`)이 대신한다. 이미 마지막 항목이 sentinel과 같으면 중복 추가하지
    않는다.

    Raises:
        ValueError: 두 `Edit`이 원문 좌표에서 겹칠 때(계약 위반 — 호출측이 `contract.violation`으로
            바꿔 올린다).
    """
    ordered = sorted(edits, key=lambda e: e.start)
    prev_end = 0
    for edit in ordered:
        if edit.start < prev_end:
            msg = f"overlapping Edit at {edit.start} (previous edit ends at {prev_end})"
            raise ValueError(msg)
        prev_end = edit.start + edit.length

    parts: list[str] = []
    offset_map: list[list[int]] = []
    orig_cursor = 0
    disp_cursor = 0
    pending_marker: list[int] | None = None  # [disp_cursor, orig_start] — 진행 중인 삭제 구간의 시작

    def flush_marker() -> None:
        nonlocal pending_marker
        if pending_marker is not None:
            offset_map.append([pending_marker[0], pending_marker[1], 0])
            pending_marker = None

    for edit in ordered:
        if edit.start > orig_cursor:
            flush_marker()
            run_len = edit.start - orig_cursor
            parts.append(original[orig_cursor : edit.start])
            offset_map.append([disp_cursor, orig_cursor, run_len])
            disp_cursor += run_len
        if edit.replacement == "":
            if pending_marker is None:
                pending_marker = [disp_cursor, edit.start]
            # else: 인접 삭제 — 기존 마커를 그대로 이어간다(§4 "인접 삭제는 마커 하나로 접음").
        else:
            flush_marker()
            parts.append(edit.replacement)
            offset_map.append([disp_cursor, edit.start, len(edit.replacement)])
            disp_cursor += len(edit.replacement)
        orig_cursor = edit.start + edit.length

    if orig_cursor < len(original):
        flush_marker()
        run_len = len(original) - orig_cursor
        parts.append(original[orig_cursor:])
        offset_map.append([disp_cursor, orig_cursor, run_len])
        disp_cursor += run_len
    else:
        # 문자열 끝에서 끝나는 삭제: 전용 마커를 만들지 않는다 — 후행 sentinel의 `original` 값이
        # 이전 실제 구간과의 차이로 삭제량을 이미 나타낸다(04-pipelines/09 §4, 계약 픽스처 001 관측).
        pending_marker = None

    display_text = "".join(parts)
    sentinel = [len(display_text), len(original), 0]
    if not offset_map or offset_map[-1] != sentinel:
        offset_map.append(sentinel)
    return display_text, offset_map


def _is_combining_continuation(ch: str) -> bool:
    """`ch`가 앞 문자와 한 클러스터로 묶일 결합 문자(라틴 발음 구별 부호 또는 조합형 자모)인지."""
    cp = ord(ch)
    if _JAMO_LO <= cp <= _JAMO_HI:
        return True
    return unicodedata.category(ch) in _COMBINING_CATEGORIES


def clean_unicode(text: str) -> tuple[str, list[Edit], dict[str, int]]:
    """N1 U1~U5를 적용해 `(working, edits, stats)`를 반환한다.

    `working`은 `text`와 길이가 같다(동일 길이 치환만 직접 반영). `edits`는 길이가 바뀌는 삭제·NFC 합성만
    담아 `apply_edits`에 넘길 수 있다. `unicodedata.category`가 `Cc`(탭·LF 제외)·`Cf`(zero-width·BOM·
    양방향 제어·U+00AD 포함)·`Co`(PUA, 15·16번 평면 포함)를 이미 구분해 주므로 `CR`(U1)도 이 셋 중
    `Cc` 삭제 규칙 하나로 처리된다(U+000D는 `Cc`).
    """
    chars = list(text)
    n = len(chars)
    edits: list[Edit] = []
    removed_control = 0
    nfd_composed = 0
    i = 0
    while i < n:
        ch = chars[i]
        cp = ord(ch)
        cat = unicodedata.category(ch)
        if (cat == "Cc" and cp not in _CC_KEEP) or cat in ("Cf", "Co"):
            edits.append(Edit(i, 1, ""))
            removed_control += 1
            i += 1
            continue
        if cp == _NBSP:
            chars[i] = " "
            i += 1
            continue
        j = i + 1
        while j < n and _is_combining_continuation(chars[j]):
            j += 1
        if j > i + 1:
            cluster = "".join(chars[i:j])
            composed = unicodedata.normalize("NFC", cluster)
            if composed != cluster:
                if len(composed) == j - i:
                    chars[i:j] = list(composed)
                else:
                    edits.append(Edit(i, j - i, composed))
                    nfd_composed += (j - i) - len(composed)
            i = j
            continue
        i += 1
    stats = {"removed_control_chars": removed_control, "nfd_composed": nfd_composed}
    return "".join(chars), edits, stats


def fold_lexical(display_text: str) -> str:
    """N11 렉시컬 뷰의 문자 단위 NFKC 폴딩 — 호환 자모(U+3130~U+318F)는 보존한다.

    전각/반각·호환 한자·기호 폴딩은 문자 하나씩 `unicodedata.normalize("NFKC", ch)`로 처리해 여러 문자를
    가로지르는 재조합(자모 연쇄 등)이 일어나지 않게 한다 — 호환 자모를 NFKC에 그대로 통과시키면 조합형
    자모(U+1100대)로 바뀌어 `NormalizedBlock` 불변식("lexical_text에 U+1100~U+11FF 잔존 없음")을 어길 수
    있어 이 구간만 예외로 둔다.
    """
    out: list[str] = []
    for ch in display_text:
        cp = ord(ch)
        if _COMPAT_JAMO_LO <= cp <= _COMPAT_JAMO_HI:
            out.append(ch)
            continue
        out.append(unicodedata.normalize("NFKC", ch))
    return "".join(out)
