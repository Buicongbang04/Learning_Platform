import pytest

from quillo import ingest


def minimal_pdf(text: str) -> bytes:
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def test_extract_text_txt_html_pdf():
    assert ingest.extract_text("a.txt", "Governing law: New York".encode()) == "Governing law: New York"
    html = b"<html><head><style>p{}</style><script>evil()</script></head><body><p>Governing</p><p>law</p></body></html>"
    text = ingest.extract_text("a.html", html)
    assert "Governing" in text and "law" in text and "evil" not in text and "p{}" not in text
    assert "Governing law New York" in ingest.extract_text("a.pdf", minimal_pdf("Governing law New York"))


def test_extract_text_rejects_unknown_type():
    with pytest.raises(ingest.UnsupportedType):
        ingest.extract_text("a.exe", b"MZ")


def test_chunk_covers_text_with_overlap():
    text = " ".join(f"word{i}" for i in range(2000))
    chunks = ingest.chunk(text, size=500, overlap=100)
    assert all(0 < len(c) <= 500 for c in chunks)
    assert chunks[0].startswith("word0 ") and chunks[-1].endswith("word1999")
    assert chunks[1].split()[0] in chunks[0]
    assert ingest.chunk("   \n ") == []


@pytest.mark.parametrize("raw, expected", [
    ("contract.pdf", "contract.pdf"),
    ("../../etc/passwd.txt", "passwd.txt"),
    ("C:\\Users\\x\\Agreement (final).txt", "Agreement _final_.txt"),
    ("...", "document"),
    ("a" * 300 + ".txt", "a" * 196 + ".txt"),
])
def test_safe_filename(raw, expected):
    assert ingest.safe_filename(raw) == expected
