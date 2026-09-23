"""`test_pdf_fast.py` 전용 최소 PDF 바이트 생성기 — reportlab 없이 순수 Python으로 유효한 PDF 1.7을 만든다.

설계 근거: F1-05 작업 지시("테스트 PDF는 reportlab 없이 pypdfium2/…로 생성이 어려우면 tests/fixtures에
소형 PDF 바이너리를 직접 만들어 사용"), `WP-105-parse-pdf-fast-pypdfium2.md` §테스트.
구성: `build_text_pdf(pages)` — 페이지별 텍스트 조작 리스트(`text_run`)로 본문 PDF를 만든다;
`text_run(x, y, size, text)` — `BT ... Tj ET` 한 조각(Type1 Helvetica, `WinAnsiEncoding`, ASCII만);
`build_image_page_pdf(...)` — 텍스트 없이 큰 원시 RGB 이미지 XObject 하나만 있는 단일 페이지 PDF.
불변식: 생성 PDF는 xref 오프셋이 실제 바이트 위치와 정확히 일치해야 pypdfium2가 연다(`FPDFText_*` 호출
전 열기 실패 시 테스트가 먼저 깨진다). 한글 등 비-Latin-1 문자는 `text_run`에 쓰지 않는다(표준 Type1
폰트라 1바이트 인코딩 한계 — heading 번호 패턴 회귀는 순수 문자열 단위 테스트로 별도 커버).
검증 계층: 1층 — `tests/adapters/parse/test_pdf_fast.py`가 이 모듈로 만든 바이트를 파싱해 검증한다.
"""

from __future__ import annotations


def _escape(text: str) -> str:
    out = []
    for ch in text:
        if ch in ("(", ")", "\\"):
            out.append("\\")
        out.append(ch)
    return "".join(out)


def text_run(x: float, y: float, size: float, text: str) -> str:
    """`BT /F1 {size} Tf {x} {y} Td ({text}) Tj ET` 한 조각(각 조각은 pdfium 추출에서 `\\r\\n`으로 분리됨)."""
    return f"BT /F1 {size} Tf {x} {y} Td ({_escape(text)}) Tj ET\n"


def _assemble(objs: dict[int, bytes], catalog_num: int) -> bytes:
    out = bytearray()
    out += b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
    offsets: dict[int, int] = {}
    max_num = max(objs)
    for num in sorted(objs):
        offsets[num] = len(out)
        out += f"{num} 0 obj\n".encode("ascii") + objs[num] + b"\nendobj\n"
    xref_offset = len(out)
    out += f"xref\n0 {max_num + 1}\n".encode("ascii")
    out += b"0000000000 65535 f \n"
    for num in range(1, max_num + 1):
        out += f"{offsets[num]:010d} 00000 n \n".encode("ascii")
    out += (f"trailer\n<< /Size {max_num + 1} /Root {catalog_num} 0 R >>\nstartxref\n{xref_offset}\n%%EOF").encode(
        "ascii"
    )
    return bytes(out)


def build_text_pdf(pages: list[str], media_box: tuple[float, float, float, float] = (0, 0, 612, 792)) -> bytes:
    """`pages[i]`는 i번째 페이지의 콘텐츠 스트림 본문(`text_run` 조각들을 이어붙인 문자열)."""
    n = len(pages)
    catalog, pages_obj, font = 1, 2, 3
    first_page = 4
    first_content = first_page + n

    objs: dict[int, bytes] = {}
    objs[catalog] = f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode("ascii")
    kids = " ".join(f"{first_page + i} 0 R" for i in range(n))
    objs[pages_obj] = f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode("ascii")
    objs[font] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"

    mb = " ".join(str(v) for v in media_box)
    for i, content in enumerate(pages):
        page_num = first_page + i
        content_num = first_content + i
        objs[page_num] = (
            f"<< /Type /Page /Parent {pages_obj} 0 R /MediaBox [{mb}] "
            f"/Resources << /Font << /F1 {font} 0 R >> >> /Contents {content_num} 0 R >>"
        ).encode("ascii")
        body = content.encode("latin-1", errors="replace")
        objs[content_num] = f"<< /Length {len(body)} >>\nstream\n".encode("ascii") + body + b"\nendstream"

    return _assemble(objs, catalog)


def build_image_page_pdf(
    *,
    media_box: tuple[float, float, float, float] = (0, 0, 612, 792),
    image_bbox: tuple[float, float, float, float] = (50, 50, 550, 750),
) -> bytes:
    """텍스트 없이 큰 단색 원시 RGB 이미지 XObject 하나만 있는 단일 페이지(저밀도/스캔 유사 픽스처)."""
    catalog, pages_obj, font, img, page, content = 1, 2, 3, 4, 5, 6
    pixel = bytes([180, 180, 180])
    objs: dict[int, bytes] = {}
    objs[catalog] = f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode("ascii")
    objs[pages_obj] = f"<< /Type /Pages /Kids [{page} 0 R] /Count 1 >>".encode("ascii")
    objs[font] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    objs[img] = (
        (
            f"<< /Type /XObject /Subtype /Image /Width 1 /Height 1 /ColorSpace /DeviceRGB "
            f"/BitsPerComponent 8 /Length {len(pixel)} >>\nstream\n"
        ).encode("ascii")
        + pixel
        + b"\nendstream"
    )

    x0, y0, x1, y1 = image_bbox
    sx, sy = x1 - x0, y1 - y0
    stream = f"q {sx} 0 0 {sy} {x0} {y0} cm /Im1 Do Q\n".encode("ascii")
    mb = " ".join(str(v) for v in media_box)
    objs[page] = (
        f"<< /Type /Page /Parent {pages_obj} 0 R /MediaBox [{mb}] "
        f"/Resources << /Font << /F1 {font} 0 R >> /XObject << /Im1 {img} 0 R >> >> /Contents {content} 0 R >>"
    ).encode("ascii")
    objs[content] = f"<< /Length {len(stream)} >>\nstream\n".encode("ascii") + stream + b"\nendstream"

    return _assemble(objs, catalog)
