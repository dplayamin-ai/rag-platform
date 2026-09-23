"""Command line entry point ``rag`` (entry-point layer; bible §12 ``cli``; commands: 10-development/02).

Phase 6A only provides the entry point and ``--version``; subcommands (``up``, ``ingest``,
``query``, ``reindex``, ``eval``, ``profile``, ``plugin``, ``cache``, ``serve``, ``mcp``) are added
by later work packages.
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
