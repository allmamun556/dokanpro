from decimal import Decimal
from collections import defaultdict

from fpdf import FPDF

from app.models.order import Order
from app.models.business import Business

DISCLAIMER = (
    "Hinweis: Diese Rechnung ist maschinell erstellt und wurde nicht auf "
    "Rechtsgueltigkeit nach Par. 14 UStG geprueft (u.a. fortlaufende "
    "Rechnungsnummer, Steuernummer). Fuer den produktiven Einsatz bitte "
    "steuerlich pruefen lassen."
)


def _bill_to(order: Order) -> list[str]:
    if order.customer:
        lines = [order.customer.name]
        if order.customer.email:
            lines.append(order.customer.email)
        return lines
    if order.guest_name:
        lines = [order.guest_name]
        if order.guest_email:
            lines.append(order.guest_email)
        return lines
    if order.table_label:
        return [f"Tisch {order.table_label}"]
    return ["Laufkundschaft"]


def generate_invoice_pdf(order: Order, business: Business) -> bytes:
    """
    Builds a single-document PDF invoice: letterhead, bill-to, itemized lines,
    VAT summary grouped by rate, footer, and an explicit disclaimer that this
    has not been reviewed for German legal (Par. 14 UStG) compliance.
    """
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, business.name or "Restaurant", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    if business.address:
        pdf.cell(0, 6, business.address, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "RECHNUNG", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Rechnung Nr: INV-{order.id:06d}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Datum: {order.created_at.strftime('%d.%m.%Y')}", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Rechnung an:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for line in _bill_to(order):
        pdf.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 9)
    col_widths = [10, 80, 20, 30, 20, 30]
    headers = ["Pos", "Artikel", "Menge", "Einzelpreis", "MwSt", "Gesamt"]
    for w, h in zip(col_widths, headers):
        pdf.cell(w, 8, h, border=1)
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    tax_by_rate: dict[Decimal, dict[str, Decimal]] = defaultdict(lambda: {"net": Decimal("0"), "tax": Decimal("0")})
    for idx, item in enumerate(order.items, start=1):
        rate = Decimal(str(item.product.tax_rate)) if item.product else Decimal("0")
        net = Decimal(str(item.unit_price)) * item.qty - Decimal(str(item.discount_amount))
        tax_by_rate[rate]["net"] += net
        tax_by_rate[rate]["tax"] += Decimal(str(item.tax_amount))

        name = item.product.name if item.product else f"Artikel #{item.product_id}"
        pdf.cell(col_widths[0], 7, str(idx), border=1)
        pdf.cell(col_widths[1], 7, name[:45], border=1)
        pdf.cell(col_widths[2], 7, str(item.qty), border=1, align="R")
        pdf.cell(col_widths[3], 7, f"{business.currency_symbol}{item.unit_price:.2f}", border=1, align="R")
        pdf.cell(col_widths[4], 7, f"{rate:.0f}%", border=1, align="R")
        pdf.cell(col_widths[5], 7, f"{business.currency_symbol}{item.line_total:.2f}", border=1, align="R")
        pdf.ln()

    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Zwischensumme (netto, pro Satz):", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for rate in sorted(tax_by_rate.keys()):
        bucket = tax_by_rate[rate]
        pdf.cell(
            0, 6,
            f"  {rate:.0f}%: Netto {business.currency_symbol}{bucket['net']:.2f} "
            f"+ MwSt {business.currency_symbol}{bucket['tax']:.2f}",
            new_x="LMARGIN", new_y="NEXT",
        )

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, f"Gesamtsumme: {business.currency_symbol}{order.total:.2f}", new_x="LMARGIN", new_y="NEXT")

    if business.receipt_footer:
        pdf.ln(6)
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, business.receipt_footer)

    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 4, DISCLAIMER)

    return bytes(pdf.output())
