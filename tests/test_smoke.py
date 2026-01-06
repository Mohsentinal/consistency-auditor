from __future__ import annotations

from consistency_auditor import __version__
from consistency_auditor.cli import main


def test_version_exists():
    assert isinstance(__version__, str)
    assert __version__.count(".") >= 1


def test_cli_version_flag(capsys):
    rc = main(["--version"])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == __version__