import zipfile
from pathlib import Path

from typer.testing import CliRunner

from moneno.docx_images import app, extract_images

PNG = b"\x89PNG\r\n\x1a\n" + b"fake-png-bytes"
JPEG = b"\xff\xd8\xff\xe0" + b"fake-jpeg-bytes"

REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def build_docx(path: Path, media: dict, rels: str = "", document: str = "") -> None:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("word/document.xml", document)
        if rels:
            zf.writestr("word/_rels/document.xml.rels", rels)
        for name, data in media.items():
            zf.writestr(f"word/media/{name}", data)


def _rels(entries):
    body = "".join(
        '<Relationship Id="{rid}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
        'Target="{target}"/>'.format(rid=rid, target=target)
        for rid, target in entries
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Relationships xmlns="{REL_NS}">{body}</Relationships>'
    )


def _document(rids):
    parts = []
    for rid in rids:
        parts.append(
            '<w:p><w:r><w:drawing>'
            '<a:blip xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
            f'r:embed="{rid}"/>'
            "</w:drawing></w:r></w:p>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f'<w:body>{"".join(parts)}</w:body></w:document>'
    )


def test_extract_byte_identical(tmp_path: Path) -> None:
    docx = tmp_path / "report.docx"
    build_docx(
        docx,
        {"image1.png": PNG, "image2.jpeg": JPEG},
        rels=_rels([("rId1", "media/image1.png"), ("rId2", "media/image2.jpeg")]),
        document=_document(["rId1", "rId2"]),
    )

    out = tmp_path / "out"
    results = extract_images(docx, out)

    assert (out / "image1.png").read_bytes() == PNG
    assert (out / "image2.jpeg").read_bytes() == JPEG
    assert {name for name, _ in results} == {"image1.png", "image2.jpeg"}


def test_ordered_prefixes(tmp_path: Path) -> None:
    # Reference image2 before image1 so the ordering is observable.
    docx = tmp_path / "report.docx"
    build_docx(
        docx,
        {"image1.png": PNG, "image2.jpeg": JPEG},
        rels=_rels([("rId1", "media/image1.png"), ("rId2", "media/image2.jpeg")]),
        document=_document(["rId2", "rId1"]),
    )

    out = tmp_path / "out"
    extract_images(docx, out, ordered=True)

    assert (out / "001_image2.jpeg").read_bytes() == JPEG
    assert (out / "002_image1.png").read_bytes() == PNG


def test_no_images_exit_1(tmp_path: Path) -> None:
    docx = tmp_path / "empty.docx"
    build_docx(docx, {}, document=_document([]))

    runner = CliRunner()
    result = runner.invoke(app, [str(docx), "-o", str(tmp_path / "out")])

    assert result.exit_code == 1
    assert "no images" in " ".join(result.output.split())


def test_non_zip_exit_1(tmp_path: Path) -> None:
    not_zip = tmp_path / "not.docx"
    not_zip.write_text("this is not a zip")

    runner = CliRunner()
    result = runner.invoke(app, [str(not_zip), "-o", str(tmp_path / "out")])

    assert result.exit_code == 1


def test_non_docx_exit_1(tmp_path: Path) -> None:
    not_docx = tmp_path / "not.docx"
    with zipfile.ZipFile(not_docx, "w") as zf:
        zf.writestr("some/file.txt", "hi")

    runner = CliRunner()
    result = runner.invoke(app, [str(not_docx), "-o", str(tmp_path / "out")])

    assert result.exit_code == 1


def test_nonempty_dir_refusal_and_force(tmp_path: Path) -> None:
    docx = tmp_path / "report.docx"
    build_docx(
        docx,
        {"image1.png": PNG},
        rels=_rels([("rId1", "media/image1.png")]),
        document=_document(["rId1"]),
    )

    out = tmp_path / "out"
    out.mkdir()
    (out / "existing.txt").write_text("keep me")

    runner = CliRunner()
    refused = runner.invoke(app, [str(docx), "-o", str(out)])
    assert refused.exit_code == 1
    assert (out / "existing.txt").read_text() == "keep me"

    forced = runner.invoke(app, [str(docx), "-o", str(out), "--force"])
    assert forced.exit_code == 0
    assert (out / "image1.png").read_bytes() == PNG
