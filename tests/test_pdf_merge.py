from pathlib import Path

from pypdf import PdfReader, PdfWriter
from typer.testing import CliRunner

from moneno.pdf_merge import app, merge_pdfs


def make_pdf(path: Path, pages: int = 1) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=792)
    with path.open("wb") as fh:
        writer.write(fh)


def test_merge_page_count(tmp_path: Path) -> None:
    a = tmp_path / "a.pdf"
    b = tmp_path / "b.pdf"
    make_pdf(a, 2)
    make_pdf(b, 3)

    out = tmp_path / "merged.pdf"
    results = merge_pdfs([a, b], out)

    assert out.exists()
    assert sum(pages for _, pages in results) == 5
    assert len(PdfReader(str(out)).pages) == 5


def test_refuse_overwrite_without_force(tmp_path: Path) -> None:
    a = tmp_path / "a.pdf"
    make_pdf(a, 1)

    out = tmp_path / "merged.pdf"
    out.write_bytes(b"existing")

    runner = CliRunner()
    result = runner.invoke(app, [str(a), "-o", str(out)])

    assert result.exit_code == 1
    assert out.read_bytes() == b"existing"


def test_force_overwrites(tmp_path: Path) -> None:
    a = tmp_path / "a.pdf"
    make_pdf(a, 1)

    out = tmp_path / "merged.pdf"
    out.write_bytes(b"existing")

    runner = CliRunner()
    result = runner.invoke(app, [str(a), "-o", str(out), "--force"])

    assert result.exit_code == 0
    assert out.read_bytes() != b"existing"
    assert len(PdfReader(str(out)).pages) == 1
