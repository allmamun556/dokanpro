import csv
import io

from fastapi import HTTPException, status
from fastapi.responses import Response
from fpdf import FPDF


def export_response(fmt: str, title: str, columns: list[str], rows: list[list]) -> Response:
    """
    Renders tabular data as a downloadable CSV or PDF.
    `columns` are the header labels; each entry in `rows` must be the same length as `columns`.
    """
    if fmt == "csv":
        return _csv_response(title, columns, rows)
    if fmt == "pdf":
        return _pdf_response(title, columns, rows)
    raise HTTPException(status.HTTP_400_BAD_REQUEST, "format must be 'csv' or 'pdf'")


def _filename(title: str, ext: str) -> str:
    return f"{title.lower().replace(' ', '_')}.{ext}"


def _csv_response(title: str, columns: list[str], rows: list[list]) -> Response:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    writer.writerows(rows)
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{_filename(title, "csv")}"'},
    )


def _pdf_response(title: str, columns: list[str], rows: list[list]) -> Response:
    pdf = FPDF(orientation="L" if len(columns) > 4 else "P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)

    usable_width = pdf.w - pdf.l_margin - pdf.r_margin
    col_width = usable_width / len(columns)

    pdf.set_font("Helvetica", "B", 9)
    for col in columns:
        pdf.cell(col_width, 8, str(col), border=1)
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    for row in rows:
        for value in row:
            pdf.cell(col_width, 7, str(value), border=1)
        pdf.ln()

    if not rows:
        pdf.cell(usable_width, 7, "No data for this period.", border=1)

    pdf_bytes = bytes(pdf.output())
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{_filename(title, "pdf")}"'},
    )
