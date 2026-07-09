import re
import dateparser

from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Invoice Extraction API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class InvoiceInput(BaseModel):
    invoice_text: str


def parse_date(text):
    d = dateparser.parse(text)

    if d:
        return d.strftime("%Y-%m-%d")

    return None


def parse_money(value):

    if value is None:
        return None

    value = value.replace(",", "")

    m = re.search(r"([0-9]+(?:\.[0-9]{1,2})?)", value)

    if m:
        return float(m.group(1))

    return None


@app.post("/extract")
def extract(data: InvoiceInput):

    text = data.invoice_text

    invoice_no = None
    vendor = None
    date = None
    amount = None
    tax = None
    currency = None

    # -------------------------
    # Invoice Number
    # -------------------------

    m = re.search(
        r"Invoice\s*(?:No|Number)?[:#]?\s*([A-Za-z0-9\-\/]+)",
        text,
        re.I,
    )

    if m:
        invoice_no = m.group(1)

    # -------------------------
    # Vendor
    # -------------------------

    m = re.search(
        r"Vendor[:\s]+(.+)",
        text,
        re.I,
    )

    if m:
        vendor = m.group(1).strip()

    # -------------------------
    # Date
    # -------------------------

    m = re.search(
        r"Date[:\s]+([^\n]+)",
        text,
        re.I,
    )

    if m:
        date = parse_date(m.group(1))

    # -------------------------
    # Subtotal
    # -------------------------

    m = re.search(
        r"Subtotal[:\sA-Za-z\.]*([0-9,]+\.\d+)",
        text,
        re.I,
    )

    if m:
        amount = parse_money(m.group(1))

    # -------------------------
    # Tax
    # -------------------------

    m = re.search(
        r"(?:GST|Tax).*?([0-9,]+\.\d+)",
        text,
        re.I,
    )

    if m:
        tax = parse_money(m.group(1))

    # -------------------------
    # Currency
    # -------------------------

    if re.search(r"\bRs\.|\bINR\b|₹", text):
        currency = "INR"

    elif re.search(r"\$", text):
        currency = "USD"

    elif re.search(r"€", text):
        currency = "EUR"

    elif re.search(r"£", text):
        currency = "GBP"

    return {
        "invoice_no": invoice_no,
        "date": date,
        "vendor": vendor,
        "amount": amount,
        "tax": tax,
        "currency": currency,
    }
