"""Recalculate sprint-queue.xlsx Dashboard KPIs from the Catalog, in pure Python.

Writes literal values into the documented Dashboard cells so ``data_only`` reads
are correct without Excel/LibreOffice. Usage:

    python recalc.py <path-to-xlsx>
"""
import sys
from openpyxl import load_workbook

LOE = {"S": 1, "M": 3, "L": 8, "XL": 20}
DISSOLVED = "Dissolved"
COMPLETED = "Completed"
ACTIVE = {"Queued", "In Flight"}


def _rows(ws):
    headers = [c.value for c in ws[1]]
    idx = {h: i for i, h in enumerate(headers) if h}
    out = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not any(v not in (None, "") for v in row):
            continue

        def g(col):
            return row[idx[col]] if col in idx and idx[col] < len(row) else None

        def s(col):
            v = g(col)
            return v.strip() if isinstance(v, str) else (v if v is not None else "")

        out.append({
            "seq": g("Seq"),
            "phase": s("Phase"),
            "loe": s("LOE"),
            "impl": s("Implementation Status"),
            "written": s("Written Status"),
        })
    return out


def _pts(loe):
    return LOE.get(str(loe).upper(), 0)


def recalc(path):
    wb = load_workbook(path)
    cat = wb["Catalog"]
    dash = wb["Dashboard"]
    rows = _rows(cat)
    live = [r for r in rows if r["impl"] != DISSOLVED]

    total = len(live)
    completed = sum(1 for r in live if r["impl"] == COMPLETED)
    in_flight = sum(1 for r in live if r["impl"] == "In Flight")
    queued = sum(1 for r in live if r["impl"] == "Queued")
    blocked = sum(1 for r in live if r["impl"] == "Blocked")
    dissolved = sum(1 for r in rows if r["impl"] == DISSOLVED)

    total_loe = sum(_pts(r["loe"]) for r in live)
    completed_loe = sum(_pts(r["loe"]) for r in live if r["impl"] == COMPLETED)
    remaining = sum(1 for r in live if r["impl"] != COMPLETED)
    loe_remaining = total_loe - completed_loe

    pct_count = (completed / total) if total else 0
    pct_loe = (completed_loe / total_loe) if total_loe else 0
    avg = (total_loe / total) if total else 0

    full_specs_queued = sum(
        1 for r in live if r["impl"] in ACTIVE and r["written"] == "Full Spec"
    )

    # Current phase = the Phase of the lowest-Seq active (Queued / In Flight) row.
    active_seq = sorted(
        (r for r in live if r["impl"] in ACTIVE and isinstance(r["seq"], (int, float))),
        key=lambda r: r["seq"],
    )
    cur_phase = active_seq[0]["phase"] if active_seq else None
    in_phase = [r for r in live if r["phase"] == cur_phase] if cur_phase else []
    phase_total = len(in_phase)
    phase_done = sum(1 for r in in_phase if r["impl"] == COMPLETED)
    phase_remaining = phase_total - phase_done
    phase_pct = (phase_done / phase_total) if phase_total else 0

    if full_specs_queued >= 5:
        health = "Healthy"
    elif full_specs_queued >= 3:
        health = "Running low"
    elif full_specs_queued >= 1:
        health = "Critical"
    else:
        health = "Empty"

    vals = {
        "B11": total, "B12": completed, "B13": in_flight, "B14": queued,
        "B15": blocked, "B16": dissolved, "B17": pct_count,
        "B20": remaining, "B21": loe_remaining, "B22": completed_loe,
        "B23": total_loe, "B24": pct_loe, "B25": avg,
        "B29": full_specs_queued, "B32": health,
        "B35": phase_total, "B36": phase_done, "B37": phase_remaining, "B38": phase_pct,
    }
    for cell, v in vals.items():
        dash[cell] = v
    wb.save(path)
    return vals


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python recalc.py <path-to-xlsx>", file=sys.stderr)
        sys.exit(2)
    out = recalc(sys.argv[1])
    print("recalc OK:", {k: out[k] for k in ("B11", "B24", "B29", "B32")})
