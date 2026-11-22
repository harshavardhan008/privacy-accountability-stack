"""Make the printable one-page handout card (US Letter, two cards per page, cut in half).

Usage:  python tools/make_card.py https://harshavardhan008.github.io/privacy-accountability-stack/agent-privacy-clinic/ card.pdf
Needs:  pip install reportlab "qrcode[pil]"
"""
import io
import sys

try:
    import qrcode
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
except ImportError:  # pragma: no cover
    sys.exit('Install helpers first: pip install reportlab "qrcode[pil]"')

NAVY = colors.HexColor("#001324")
BLUE = colors.HexColor("#0a66d6")
GREY = colors.HexColor("#51627a")

CHECKS = [
    ("Purpose", "Checked at every tool call"),
    ("Minimization", "Only the fields that purpose needs"),
    ("Record", "One per action, denials included, no data"),
    ("Approval", "A person approves writes and sends"),
    ("Sandbox", "Synthetic data first, real business rules"),
]
FIELDS = "Request, Delegator, Agent and version, Purpose, Tool and operation, Data classes, Consent reference, Approval, Destination and retention"


def card(c, x, y, w, h, url):
    c.setStrokeColor(colors.HexColor("#d5dde8"))
    c.setDash(3, 3)
    c.rect(x, y, w, h)
    c.setDash()
    pad = 22
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 17)
    c.drawString(x + pad, y + h - 36, "Agent privacy checklist")
    c.setFillColor(GREY)
    c.setFont("Helvetica", 9.5)
    c.drawString(x + pad, y + h - 52, "Before an AI agent touches personal data. Think of one agent you run.")
    yy = y + h - 82
    for i, (name, desc) in enumerate(CHECKS, 1):
        c.setFillColor(BLUE)
        c.circle(x + pad + 8, yy + 4, 8, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(x + pad + 8, yy + 0.5, str(i))
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x + pad + 24, yy + 5, name)
        c.setFillColor(GREY)
        c.setFont("Helvetica", 9.5)
        c.drawString(x + pad + 24, yy - 7, desc)
        yy -= 34
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(x + pad, y + 78, "The Action Record, nine fields. Classes and hashes, never the data.")
    c.setFillColor(GREY)
    c.setFont("Helvetica", 8.5)
    words, line, ly = FIELDS.split(" "), "", y + 64
    for wd in words:
        if c.stringWidth(line + wd, "Helvetica", 8.5) > w - 2 * pad - 90:
            c.drawString(x + pad, ly, line)
            line, ly = "", ly - 11
        line += wd + " "
    c.drawString(x + pad, ly, line)
    qr = qrcode.make(url, box_size=6, border=1)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    buf.seek(0)
    c.drawImage(ImageReader(buf), x + w - pad - 72, y + 14, 72, 72)
    c.setFont("Helvetica", 7.5)
    c.setFillColor(GREY)
    c.drawString(x + pad, y + 14, "Scan to score yourself: one minute, anonymous.")
    c.drawString(x + pad, y + 5, "Harshavardhan Peddireddy | ETIC 2026")


def main(argv):
    if len(argv) != 3 or not argv[1].startswith("http"):
        sys.exit(__doc__)
    c = canvas.Canvas(argv[2], pagesize=letter)
    W, H = letter
    for i in range(2):
        card(c, 36, 36 + i * (H - 72) / 2, W - 72, (H - 72) / 2 - 6, argv[1])
    c.save()
    print(f"wrote {argv[2]}")


if __name__ == "__main__":
    main(sys.argv)
