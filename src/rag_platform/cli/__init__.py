"""명령행 진입점 `rag`(진입점 계층; 바이블 §12 `cli`; 명령 상세는 10-development/02·WP-503).

설계 근거: 바이블 §12(모듈 맵), 10-development/02(CLI 명령 사양); `docs/13-implementation/wp/
WP-503-cli-and-full-e2e.md`(F5-03이 하위 명령 실 구현을 `cli/main.py`에 추가).
구성: `main(argv)` — `--version`/빈 인자/`-h`·`--help`는 6A 시절 그대로 처리하고, 그 외 인자가
등록된 하위 명령(`ingest`/`query`/`serve`/`profile`)으로 시작하면 `cli.main.main`(argparse 실
구현, 아래 `_dispatch`)에 위임한다.
불변식·주의: 이 파일과 `cli/main.py`는 같은 이름 `main`을 두고 경쟁한다 — 파이썬은 서브모듈이
처음 로드되는 순간 부모 패키지의 동명 속성을 그 모듈 객체로 덮어쓴다(임포트 구문 종류와 무관한
부작용). 그래서 이 파일이 "이 패키지가 처음 임포트될 때" 그 부작용을 스스로 일으키고 곧바로
`def main`으로 되돌려 놓는다: 아래 `from rag_platform.cli.main import main as _dispatch`가 먼저
`rag_platform.cli.main` 서브모듈을 로드시키고(그 순간 `rag_platform.cli.main` 속성이 일시적으로
모듈이 된다) `cli/main.py`의 진짜 `main` 함수를 `_dispatch`로 받아 두며, 그다음 `def main(...)`이
이 패키지의 `main` 속성을 다시 함수로 덮어써 최종 상태를 고정한다. 이 순서는 `rag_platform.cli`가
처음 임포트되는 시점(다른 어떤 파일이 먼저 손대든)에 항상 지켜지므로, 이후 어디서
`import rag_platform.cli.main`을 하더라도(서브모듈은 이미 캐시돼 있어 부작용이 재발하지 않는다)
이 패키지의 `main` 속성은 함수로 유지된다(open_issues: 이름 충돌 주의). `pyproject.toml`의
`[project.scripts] rag = "rag_platform.cli:main"`은 이 보장 덕분에 이 파일의 함수를 가리킨다.
`tests/e2e/test_full_e2e.py`는 `importlib.import_module("rag_platform.cli.main")`로 서브모듈
자체를 가져온다(그 함수는 `sys.modules`를 이름으로 직접 조회해 속성값과 무관하게 항상 서브모듈을
돌려준다 — `import rag_platform.cli.main as cli_main` 구문은 속성을 거쳐가므로 피한다).
검증 계층: 1층(여기서 검증) — `tests/unit/test_scaffold.py`(6A `--version`/오류 표면),
`tests/e2e/test_full_e2e.py`(하위 명령은 서브모듈을 직접 호출해 이 위임 경로 밖에서도 검증).
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import rag_platform

# 아래 `def main`이 이 이름을 다시 정의해 이 패키지의 `main` 속성을 함수로 되돌린다(모듈 docstring
# 참고) — `_dispatch`는 `cli/main.py`의 진짜 argparse 진입점을 그대로 가리킨다.
from rag_platform.cli.main import main as _dispatch

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["main"]

_USAGE = "usage: rag [--version]\n"
_SUBCOMMANDS = ("ingest", "query", "serve", "profile")


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
    if args and args[0] in _SUBCOMMANDS:
        return _dispatch(args)
    sys.stderr.write(_USAGE)
    return 0 if not args or args in (["-h"], ["--help"]) else 2
