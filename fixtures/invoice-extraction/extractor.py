"""A deliberately format-fragile invoice field extractor.

This is a TEACHING FIXTURE, not a real product. It is intentionally naive:
it assumes the eleven invoice fields always arrive one-per-line in a fixed
order, and it reads each value by its LINE POSITION rather than by the label
in front of it. On consistently formatted input it looks flawless. When the
field order or line structure shifts, it silently assigns values to the wrong
fields and still returns clean, well-formed output. That is the point: it has
learned layout, not meaning, which is exactly the failure production-autopsy
is built to surface.
"""

FIELDS = [
    "invoice_id", "vendor", "client", "date", "item", "quantity",
    "unit_price", "total", "currency", "payment_terms", "po_number",
]

_DELIMS = [": ", " | ", " => ", "\t", ": ", ":", "|", "=>", ",", "  "]


def _value_after_label(line):
    """Strip a leading 'Label<delim>value' down to value. If no delimiter is
    found, return the whole line. This part is robust on purpose; the fragility
    is the positional field assignment, not the value parsing."""
    for d in _DELIMS:
        if d in line:
            return line.split(d, 1)[1].strip()
    return line.strip()


def extract(text):
    """Return {field: value}, assigned by line position (the fragile part)."""
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    out = {}
    for i, field in enumerate(FIELDS):
        out[field] = _value_after_label(lines[i]) if i < len(lines) else ""
    return out
