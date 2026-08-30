import re
import pdfplumber
from datetime import datetime

CREDIT_RE = re.compile(
    r"(?P<date>[A-Za-z]{3}\s+\d{1,2},\s+\d{4})"
    r".{0,80}?Received from\s+(?P<sender>.*?)\s+CREDIT\s+₹(?P<amount>[\d,]+(?:\.\d+)?)"
    r".{0,100}?Transaction ID\s+(?P<transaction_id>[A-Za-z0-9]+)"
    r".{0,80}?UTR No\.\s+(?P<utr>[A-Za-z0-9]+)",
    re.IGNORECASE | re.DOTALL
)

def clean_spaces(value):
    return re.sub(r"\s+", " ", value or "").strip()

def parse_bank_statement(pdf_file):
    text = "\n".join(page.extract_text() or "" for page in pdfplumber.open(pdf_file).pages)

    # Normalize line wrapping while retaining enough structure for the regex.
    text = text.replace("\r", "\n")

    transactions = []
    for m in CREDIT_RE.finditer(text):
        date = datetime.strptime(m.group("date"), "%b %d, %Y").date()
        transactions.append({
            "date": date,
            "time": "",
            "sender": clean_spaces(m.group("sender")),
            "amount": float(m.group("amount").replace(",", "")),
            "transaction_id": clean_spaces(m.group("transaction_id")),
            "utr": clean_spaces(m.group("utr")),
            "type": "CREDIT",
            "raw": clean_spaces(m.group(0))
        })

    # PhonePe statements can place time on the next line. Extract it from
    # the transaction block when possible.
    for tx in transactions:
        pattern = re.escape(tx["date"].strftime("%b %d, %Y")) + r".{0,180}?" + re.escape(tx["transaction_id"])
        block = re.search(pattern, text, re.I | re.S)
        if block:
            tm = re.search(r"(\d{1,2}:\d{2}\s*[ap]m)", block.group(0), re.I)
            if tm:
                tx["time"] = tm.group(1).lower().replace(" ", "")

    return transactions
