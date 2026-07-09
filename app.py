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
    
    invoice_patterns = [
        r"Invoice\s*(?:No|Number)?\s*[:#]\s*([A-Za-z0-9\-\/]+)",
        r"Inv\s*(?:No|Number)?\s*[:#]\s*([A-Za-z0-9\-\/]+)",
        r"Bill\s*(?:No|Number)?\s*[:#]\s*([A-Za-z0-9\-\/]+)",
        r"Ref(?:erence)?\s*[:#]?\s*([A-Za-z0-9\-\/]+)",
        r"Reference\s*[:#]?\s*([A-Za-z0-9\-\/]+)",
    ]
    
    for pattern in invoice_patterns:
        m = re.search(pattern, text, re.I)
        if m:
            invoice_no = m.group(1).strip()
            break

    # -------------------------
    # Vendor
    # -------------------------

    vendor_patterns = [
        r"Vendor\s*:\s*(.+)",
        r"Supplier\s*:\s*(.+)",
        r"Company\s*:\s*(.+)",
        r"Seller\s*:\s*(.+)",
        r"From\s*:\s*(.+)",
    ]
    
    for pattern in vendor_patterns:
        m = re.search(pattern, text, re.I)
        if m:
            vendor = m.group(1).strip()
            break

    # -------------------------
    # Date
    # -------------------------

    date_patterns = [
        r"Date\s*:\s*(.+)",
        r"Issued\s*:\s*(.+)",
        r"Invoice Date\s*:\s*(.+)",
        r"Billing Date\s*:\s*(.+)",
    ]
    
    for pattern in date_patterns:
        m = re.search(pattern, text, re.I)
        if m:
            date = parse_date(m.group(1).strip())
            break
            
    # -------------------------
    # Subtotal
    # -------------------------

    amount_patterns = [
        r"Subtotal\s*:?\s*(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.\d+)?)",
        r"Sub\s*Total\s*:?\s*(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.\d+)?)",
        r"Net Amount\s*:?\s*(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.\d+)?)",
        r"Taxable Value\s*:?\s*(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.\d+)?)",
        r"Amount Before Tax\s*:?\s*(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.\d+)?)",
        r"Basic Amount\s*:?\s*(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.\d+)?)",
        r"Amount\s*:?\s*(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.\d+)?)",
    ]
    
    for pattern in amount_patterns:
        m = re.search(pattern, text, re.I)
        if m:
            amount = parse_money(m.group(1))
            break

    # -------------------------
    # Tax
    # -------------------------
    tax_patterns = [
        r"GST.*?([0-9,]+(?:\.\d+)?)",
        r"IGST.*?([0-9,]+(?:\.\d+)?)",
        r"CGST.*?([0-9,]+(?:\.\d+)?)",
        r"SGST.*?([0-9,]+(?:\.\d+)?)",
        r"VAT.*?([0-9,]+(?:\.\d+)?)",
        r"Tax.*?([0-9,]+(?:\.\d+)?)",
    ]
    
    for pattern in tax_patterns:
        m = re.search(pattern, text, re.I)
        if m:
            tax = parse_money(m.group(1))
            break

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
