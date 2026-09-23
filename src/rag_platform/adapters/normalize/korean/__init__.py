"""`normalizer.chain`의 문자 단위 정규화 하위 모듈 모음(N1 `unicode`, N2 `linebreaks`).

역할: `stage.py`가 오케스트레이션하는 블록 단위 편집 두 단계 — 유니코드 정리(`unicode.py`)와 줄바꿈
병합·하이픈 결합(`layout.py`) — 를 담는 패키지. 둘 다 원문 좌표계에서만 편집을 기록하는 순수 함수라
`ParsedDocument.Block.text`를 직접 읽는 `stage.py` 외에는 다른 모듈이 몰라도 된다.
설계 근거: 바이블 §12(`adapters/normalize/korean`), 04-pipelines/09 §2(N1~N2)·§4(오프셋 유지 규칙).
구성: `unicode` — `Edit`/`apply_edits`/`clean_unicode`/`fold_lexical`; `layout` — `merge_linebreaks`.
불변식: 이 패키지의 함수는 모두 순수(부작용 없음)이며 `ctx`·`storage`를 참조하지 않는다 — 분석기 훅은
호출자가 콜러블로 주입한다(`korean_join`).
검증 계층: 1층(여기서 검증) — `tests/adapters/normalize/test_normalize.py`.
"""

from __future__ import annotations
