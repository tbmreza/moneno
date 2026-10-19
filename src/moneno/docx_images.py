"""Extract original-quality images from a .docx (a zip of ``word/media/*``)."""

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import List, Tuple

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer()

console = Console()
err_console = Console(stderr=True)

REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
R_EMBED = f"{{{REL_NS}}}embed"
R_ID = f"{{{REL_NS}}}id"


class DocxError(Exception):
    """Expected, user-facing .docx extraction error."""


def _media_members(zf: zipfile.ZipFile) -> List[str]:
    return [
        name
        for name in zf.namelist()
        if name.startswith("word/media/") and not name.endswith("/")
    ]


def _ordered_members(zf: zipfile.ZipFile, members: List[str]) -> List[str]:
    """Order members by appearance in ``word/document.xml`` (via its rels)."""
    rels_path = "word/_rels/document.xml.rels"
    doc_path = "word/document.xml"

    rel_map: dict = {}
    if rels_path in zf.namelist():
        root = ET.fromstring(zf.read(rels_path))
        for rel in root:
            rid = rel.get("Id")
            target = rel.get("Target")
            if rid and target:
                rel_map[rid] = Path(target).name

    by_name = {Path(m).name: m for m in members}
    ordered: List[str] = []
    if doc_path in zf.namelist():
        root = ET.fromstring(zf.read(doc_path))
        for el in root.iter():
            rid = el.get(R_EMBED) or el.get(R_ID)
            if rid and rid in rel_map:
                name = rel_map[rid]
                if name in by_name and name not in ordered:
                    ordered.append(name)

    # Append any media not referenced in document.xml (sorted) so nothing is lost.
    remaining = sorted(set(by_name) - set(ordered))
    ordered.extend(remaining)

    return [by_name[name] for name in ordered if name in by_name]


def extract_images(docx: Path, out_dir: Path, ordered: bool = False) -> List[Tuple[str, int]]:
    """Extract ``word/media/*`` from *docx* into *out_dir*.

    Copies bytes verbatim (no re-encoding). Uses only the basename of each zip
    member (zip-slip safe). Returns ``[(output_filename, byte_size), ...]``.
    """
    docx = Path(docx)
    out_dir = Path(out_dir)

    try:
        zf = zipfile.ZipFile(docx)
    except zipfile.BadZipFile as exc:
        raise DocxError(f"'{docx}' is not a valid .docx (zip) file.") from exc
    except FileNotFoundError as exc:
        raise DocxError(f"Input file not found: {docx}") from exc

    with zf:
        if "word/document.xml" not in zf.namelist():
            raise DocxError(f"'{docx}' is not a .docx file (missing word/document.xml).")

        members = _media_members(zf)
        if not members:
            raise DocxError(f"'{docx}' contains no images (no word/media/*).")

        if ordered:
            members = _ordered_members(zf, members)

        out_dir.mkdir(parents=True, exist_ok=True)
        results: List[Tuple[str, int]] = []
        for index, member in enumerate(members, start=1):
            name = Path(member).name
            if ordered:
                name = f"{index:03d}_{name}"
            data = zf.read(member)
            (out_dir / name).write_bytes(data)
            results.append((name, len(data)))

    return results


@app.command()
def main(
    docx: Path = typer.Argument(..., help="Path to the .docx file"),
    output: Path = typer.Option(None, "-o", "--output", help="Output directory for images"),
    force: bool = typer.Option(False, "--force", help="Allow writing into a non-empty directory"),
    ordered: bool = typer.Option(
        False, "--ordered", help="Prefix files 001_, 002_... by order of appearance in the document"
    ),
) -> None:
    """Extract original-quality images from a .docx file."""
    out_dir = output if output is not None else docx.with_name(docx.stem + "_images")

    if out_dir.exists() and any(out_dir.iterdir()) and not force:
        err_console.print(
            f"[red]Output directory is not empty: {out_dir} (use --force to proceed)[/red]"
        )
        raise typer.Exit(1)

    try:
        results = extract_images(docx, out_dir, ordered=ordered)
    except DocxError as exc:
        err_console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    table = Table(title="Extracted images")
    table.add_column("Name")
    table.add_column("Size", justify="right")
    for name, size in results:
        table.add_row(name, f"{size:,} bytes")
    console.print(table)
    console.print(f"Extracted {len(results)} image(s) to {out_dir}")


if __name__ == "__main__":
    app()
