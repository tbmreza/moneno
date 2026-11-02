"""Decode a QR code from an image file and print the string it contains."""

import sys
from pathlib import Path

import zxingcpp
from PIL import Image


def main() -> None:
    """Entry point."""
    if len(sys.argv) < 2:
        print("Usage: moneno-x sample_experiment <image-file>", file=sys.stderr)
        raise SystemExit(2)

    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"File not found: {path}", file=sys.stderr)
        raise SystemExit(2)

    image = Image.open(path).convert("RGB")
    results = zxingcpp.read_barcodes(image)

    if not results:
        print("No QR code found.", file=sys.stderr)
        raise SystemExit(1)

    for result in results:
        print(result.text)


if __name__ == "__main__":
    main()
