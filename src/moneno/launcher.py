"""`moneno-x`: discover and run experiments in ``src/moneno/experimental/``."""

import ast
import difflib
import re
import runpy
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(no_args_is_help=False)

console = Console()
err_console = Console(stderr=True)

NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")

TEMPLATE = '''"""{name}: one-line summary."""

import sys


def main() -> None:
    """Entry point."""
    print(sys.argv[1:])


if __name__ == "__main__":
    main()
'''


def experiments_dir() -> Path:
    return Path(__file__).resolve().parent / "experimental"


def discover(directory: Path) -> List[Tuple[str, str]]:
    """Return ``[(name, summary), ...]`` for ``*.py`` files in *directory*.

    Only flat ``*.py`` files are considered; names starting with ``_`` are
    skipped. Docstring summaries are read with ``ast`` (no import). A file that
    cannot be parsed is listed with summary ``(unparseable)``.
    """
    directory = Path(directory)
    results: List[Tuple[str, str]] = []
    for path in sorted(directory.glob("*.py")):
        if path.name.startswith("_"):
            continue
        results.append((path.stem, _summary(path)))
    return results


def _summary(path: Path) -> str:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return "(unparseable)"
    doc = ast.get_docstring(tree)
    if not doc:
        return ""
    lines = doc.strip().splitlines()
    return lines[0].strip() if lines else ""


def scaffold(name: str, directory: Path) -> Path:
    """Create ``directory/<name>.py`` from the template. Returns the path.

    Raises ``ValueError`` for an invalid name or if the file already exists.
    """
    if not NAME_RE.match(name):
        raise ValueError(f"Invalid experiment name '{name}' (must match ^[a-z][a-z0-9_]*$)")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{name}.py"
    if target.exists():
        raise ValueError(f"Refusing to overwrite existing experiment: {target}")
    target.write_text(TEMPLATE.format(name=name), encoding="utf-8")
    return target


def complete_experiment(incomplete: str):
    for name, _ in discover(experiments_dir()):
        if name.startswith(incomplete):
            yield name


def _run(name: str, args: List[str]) -> None:
    directory = experiments_dir()
    known = {n for n, _ in discover(directory)}
    if name not in known:
        err_console.print(f"[red]Unknown experiment: {name!r}[/red]")
        suggestions = difflib.get_close_matches(name, sorted(known), n=3, cutoff=0.5)
        if suggestions:
            err_console.print("Did you mean: " + ", ".join(suggestions) + "?")
        raise typer.Exit(2)

    sys.argv = [name, *args]
    try:
        runpy.run_module(f"moneno.experimental.{name}", run_name="__main__")
    except ModuleNotFoundError as exc:
        missing = exc.name or ""
        if missing.startswith("moneno."):
            raise
        err_console.print(f"[red]Missing dependency '{missing}'.[/red]")
        err_console.print(f"Run: uv add --optional experimental {missing} && make setup")
        raise typer.Exit(1)


def _list() -> None:
    table = Table(title="Experiments")
    table.add_column("Name")
    table.add_column("Description")
    for name, summary in discover(experiments_dir()):
        table.add_row(name, summary)
    console.print(table)


def _new(name: str) -> None:
    try:
        path = scaffold(name, experiments_dir())
    except ValueError as exc:
        err_console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)
    console.print(f"[green]Created {path}[/green]")
    console.print(f"Run it with: moneno-x {name}")


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def main(
    ctx: typer.Context,
    name: Optional[str] = typer.Argument(
        None, autocompletion=complete_experiment, help="Experiment name to run"
    ),
    list_experiments: bool = typer.Option(False, "--list", help="List available experiments"),
    new: Optional[str] = typer.Option(None, "--new", help="Scaffold a new experiment"),
) -> None:
    """Run or scaffold experimental scripts.

    Flags that collide with the launcher's own flags (such as ``--help``) must
    be separated from the experiment's args with ``--``.
    """
    if new is not None:
        _new(new)
    elif name is None or list_experiments:
        _list()
    else:
        _run(name, list(ctx.args))


if __name__ == "__main__":
    app()
