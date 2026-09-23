"""명령행 진입점 `rag`(진입점 계층; 바이블 §12 `cli`; 명령 상세는 10-development/02).

설계 근거: 바이블 §12(모듈 맵), 10-development/02(CLI 명령 사양).
구성: `main(argv)` — 인자를 파싱해 `--version`을 처리하고, 그 외에는 사용법을 출력한다.
불변식: 6A 단계에서는 진입점과 `--version`만 제공한다; 하위 명령(`up`, `ingest`, `query`, `reindex`,
`eval`, `profile`, `plugin`, `cache`, `serve`, `mcp`)은 이후 작업 패키지가 추가한다.
검증 계층: 1층(여기서 검증) — 하위 명령 추가 시 개별 단위 테스트로 검증.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import rag_platform

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["main"]

_USAGE = "usage: rag [--version]\n"


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ``rag`` command line interface.

    Args:
        argv: Arguments without the program name; defaults to ``sys.argv[1:]``.

    Returns:
        Process exit code.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ["--version"]:
        sys.stdout.write(f"rag-platform {rag_platform.__version__}\n")
        return 0
    sys.stderr.write(_USAGE)
    return 0 if not args or args in (["-h"], ["--help"]) else 2
