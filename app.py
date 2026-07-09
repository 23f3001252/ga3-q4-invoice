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

    print("=" * 50)
    print(data.invoice_text)
    print("=" * 50)
    
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
        r"Issued By\s*:\s*(.+)",
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
    
    amount = None

    amount_patterns = [
        r"Subtotal.*?([0-9][0-9,]*(?:\.\d+)?)",
        r"Sub\s*Total.*?([0-9][0-9,]*(?:\.\d+)?)",
        r"Taxable\s*Value.*?([0-9][0-9,]*(?:\.\d+)?)",
        r"Taxable\s*Amount.*?([0-9][0-9,]*(?:\.\d+)?)",
        r"Amount\s*Before\s*Tax.*?([0-9][0-9,]*(?:\.\d+)?)",
        r"Net\s*Amount.*?([0-9][0-9,]*(?:\.\d+)?)",
        r"Basic\s*Amount.*?([0-9][0-9,]*(?:\.\d+)?)",
    ]
    
    for pattern in amount_patterns:
        m = re.search(pattern, text, re.I | re.S)
        if m:
            amount = parse_money(m.group(1))
            break

    if amount is None:
        for line in text.splitlines():
            lower = line.lower()
    
            # Skip tax and grand total lines
            if any(x in lower for x in ["gst", "igst", "cgst", "sgst", "vat"]):
                continue
    
            if lower.startswith("total"):
                continue
    
            numbers = re.findall(r"[0-9][0-9,]*(?:\.\d+)?", line)
    
            if "amount" in lower and numbers:
                amount = parse_money(numbers[-1])
                break

    # -------------------------
    # Tax
    # -------------------------
    # tax_patterns = [
    #     r"GST.*?([0-9,]+(?:\.\d+)?)",
    #     r"IGST.*?([0-9,]+(?:\.\d+)?)",
    #     r"CGST.*?([0-9,]+(?:\.\d+)?)",
    #     r"SGST.*?([0-9,]+(?:\.\d+)?)",
    #     r"VAT.*?([0-9,]+(?:\.\d+)?)",
    #     r"Tax.*?([0-9,]+(?:\.\d+)?)",
    # ]
    
    tax = None

    for line in text.splitlines():
        lower = line.lower()
        
        if any(keyword in lower for keyword in [
            "gst", "igst", "cgst", "sgst", "vat", "tax"
        ]):
            # Find all numbers in the line
            numbers = re.findall(r"[0-9][0-9,]*(?:\.\d+)?", line)
        
            if numbers:
                # Tax amount is usually the LAST number
                tax = parse_money(numbers[-1])
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
