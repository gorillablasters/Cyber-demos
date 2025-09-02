import csv
from io import StringIO
from datetime import date, timedelta
from typing import Iterable, Dict
from app.models import TxType, Frequency


def parse_csv_transactions(content: str) -> list[dict]:
    """
    Expected headers: name,type,category,amount,date,frequency
    - type: income|expense
    - date: YYYY-MM-DD (required if frequency=once)
    - frequency: once|weekly|bi-weekly|monthly|quarterly|yearly
    """
    out = []
    reader = csv.DictReader(StringIO(content))
    for i, row in enumerate(reader, start=1):
        try:
            tx_type = TxType(row["type"].strip())
            freq = Frequency(row.get("frequency", "once").strip() or "once")
            amt = float(row["amount"])
            cat = row.get("category") or None
            dt = row.get("date") or None
            out.append(
                {
                    "name": row["name"].strip(),
                    "type": tx_type,
                    "category": cat if tx_type == TxType.expense else None,
                    "amount": amt,
                    "frequency": freq,
                    "date": None if not dt else date.fromisoformat(dt),
                }
            )
        except Exception as e:
            raise ValueError(f"CSV row {i} invalid: {e}")
    return out


def expand_recurring(
    start: date, end: date, start_date: date, freq: Frequency
) -> Iterable[date]:
    """Yield occurrence dates (inclusive) for a recurrence starting at start_date."""
    if start_date > end:
        return []
    cur = max(start_date, start)
    step = None
    if freq == Frequency.weekly:
        step = timedelta(weeks=1)
    elif freq == Frequency.bi_weekly:
        step = timedelta(weeks=2)
    elif freq == Frequency.monthly:
        step = "monthly"
    elif freq == Frequency.quarterly:
        step = "quarterly"
    elif freq == Frequency.yearly:
        step = "yearly"
    else:
        return [start_date] if start <= start_date <= end else []

    dates = []
    d = start_date
    if d < cur:
        d = cur
    while d <= end:
        dates.append(d)
        if step == timedelta(weeks=1) or step == timedelta(weeks=2):
            d = d + step
        elif step == "monthly":
            y, m = d.year, d.month
            m = 1 if m == 12 else m + 1
            y = y + 1 if m == 1 else y
            d = date(y, m, min(d.day, 28))
        elif step == "quarterly":
            y, m = d.year, d.month
            m += 3
            while m > 12:
                m -= 12
                y += 1
            d = date(y, m, min(d.day, 28))
        elif step == "yearly":
            d = date(d.year + 1, d.month, min(d.day, 28))
    return dates
