from pathlib import Path

from typer.testing import CliRunner

from moneno import launcher


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_discover_skips_underscore(tmp_path: Path) -> None:
    _write(tmp_path / "good.py", '"""A good one."""\n')
    _write(tmp_path / "_hidden.py", '"""Hidden."""\n')
    _write(tmp_path / "not_python.txt", "nope")

    names = [name for name, _ in launcher.discover(tmp_path)]

    assert "good" in names
    assert "_hidden" not in names
    assert "not_python" not in names


def test_syntax_error_does_not_break_listing(tmp_path: Path) -> None:
    _write(tmp_path / "broken.py", "def ::\n")
    _write(tmp_path / "ok.py", '"""A summary line."""\n')

    results = dict(launcher.discover(tmp_path))

    assert results["ok"] == "A summary line."
    assert results["broken"] == "(unparseable)"


def test_unknown_name_exit_2(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(launcher, "experiments_dir", lambda: tmp_path)
    _write(tmp_path / "sample_experiment.py", '"""Example."""\n')

    runner = CliRunner()
    result = runner.invoke(launcher.app, ["sample_experimnt"])

    assert result.exit_code == 2
    assert "sample_experiment" in result.output


def test_new_refuses_bad_name(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(launcher, "experiments_dir", lambda: tmp_path)

    runner = CliRunner()
    result = runner.invoke(launcher.app, ["--new", "1bad_name"])

    assert result.exit_code == 1
    assert not (tmp_path / "1bad_name.py").exists()


def test_new_refuses_overwrite(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(launcher, "experiments_dir", lambda: tmp_path)
    _write(tmp_path / "taken.py", '"""Already here."""\n')

    runner = CliRunner()
    result = runner.invoke(launcher.app, ["--new", "taken"])

    assert result.exit_code == 1
    assert (tmp_path / "taken.py").read_text() == '"""Already here."""\n'


def test_new_scaffolds(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(launcher, "experiments_dir", lambda: tmp_path)

    runner = CliRunner()
    result = runner.invoke(launcher.app, ["--new", "my_idea"])

    assert result.exit_code == 0
    path = tmp_path / "my_idea.py"
    assert path.exists()
    assert "def main()" in path.read_text()
    assert "my_idea" in result.output


def test_cli_argument_forwarding(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(launcher, "experiments_dir", lambda: tmp_path)
    _write(tmp_path / "exp.py", 'import sys\nif __name__ == "__main__": print("ARGS:", sys.argv[1:])\n')

    monkeypatch.setattr("sys.argv", ["moneno-x", "exp", "--help", "-v"])
    called = False

    def fake_run(name, args):
        nonlocal called
        assert name == "exp"
        assert args == ["--help", "-v"]
        called = True

    monkeypatch.setattr(launcher, "_run", fake_run)
    launcher.cli()
    assert called
