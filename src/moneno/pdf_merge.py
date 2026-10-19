"""Merge PDFs into a single file."""

from pathlib import Path
from typing import List, Sequence, Tuple

import typer
from pypdf import PdfReader, PdfWriter
from rich.console import Console
from rich.table import Table

app = typer.Typer()

console = Console()
err_console = Console(stderr=True)


def merge_pdfs(inputs: Sequence[Path], output: Path) -> List[Tuple[str, int]]:
    """Merge *inputs* into *output*, in order.

    Returns ``[(filename, page_count), ...]`` for each input. Uses
    ``PdfWriter.append`` (``PdfMerger`` was removed in pypdf 5).
    """
    writer = PdfWriter()
    results: List[Tuple[str, int]] = []
    for raw in inputs:
        path = Path(raw)
        reader = PdfReader(str(path))
        writer.append(reader)
        results.append((path.name, len(reader.pages)))
    output = Path(output)
    with output.open("wb") as fh:
        writer.write(fh)
    return results


def _is_pdf(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            return fh.read(5) == b"%PDF-"
    except OSError:
        return False


@app.command()
def main(
    inputs: List[Path] = typer.Argument(..., help="PDF files to merge, in order"),
    output: Path = typer.Option(Path("merged.pdf"), "-o", "--output", help="Output PDF path"),
    force: bool = typer.Option(False, "--force", help="Overwrite the output file if it exists"),
) -> None:
    """Merge the given PDF files into a single PDF."""
    for path in inputs:
        if not path.is_file():
            err_console.print(f"[red]Input file not found: {path}[/red]")
            raise typer.Exit(1)
        if not _is_pdf(path):
            err_console.print(f"[red]Not a PDF file: {path}[/red]")
            raise typer.Exit(1)

    if output.exists() and not force:
        err_console.print(
            f"[red]Output file already exists: {output} (use --force to overwrite)[/red]"
        )
        raise typer.Exit(1)

    results = merge_pdfs(inputs, output)
    total = sum(pages for _, pages in results)

    table = Table(title="Merged PDF")
    table.add_column("File")
    table.add_column("Pages", justify="right")
    for name, pages in results:
        table.add_row(name, str(pages))
    console.print(table)
    console.print(f"[green]Total pages: {total}[/green]")
    console.print(f"Output: {output}")


if __name__ == "__main__":
    app()
