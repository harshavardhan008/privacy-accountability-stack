"""Make a QR code PNG for the scorecard page.

Usage:  python tools/make_qr.py https://harshavardhan008.github.io/privacy-accountability-stack/agent-privacy-clinic/ scorecard_qr.png
Needs:  pip install "qrcode[pil]"
"""
import sys

try:
    import qrcode
except ImportError:  # pragma: no cover
    sys.exit('Install the helper first: pip install "qrcode[pil]"')


def main(argv):
    if len(argv) != 3 or not argv[1].startswith("http"):
        sys.exit(__doc__)
    img = qrcode.make(argv[1], box_size=12, border=3)
    img.save(argv[2])
    print(f"wrote {argv[2]} for {argv[1]}")


if __name__ == "__main__":
    main(sys.argv)
