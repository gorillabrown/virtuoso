import os, subprocess, sys
from openpyxl import load_workbook, Workbook

HERE = os.path.dirname(os.path.abspath(__file__))

HEADERS = ["Priority", "Seq", "Sprint Code", "Phase", "Stage", "Title", "LOE",
           "Dependencies", "Implementation Status", "Written Status", "Branch",
           "Date Started", "Date Completed", "Close-Out File", "Description",
           "Done?", "PhaseRank", "SizeRank", "SortKey"]


def _make_workbook(path):
    wb = Workbook()
    wb.active.title = "Dashboard"  # recalc writes here; cells autocreate
    cat = wb.create_sheet("Catalog")
    cat.append(HEADERS)
    rows = [
        [1, 1, "EX-1", "Phase 1", "", "T", "M", "", "Queued", "Full Spec"],
        [2, 2, "EX-2", "Phase 1", "", "T", "S", "", "Completed 2026-06-29", "Full Spec"],
        [3, 3, "EX-3", "Phase 1", "", "T", "L", "", "Blocked", "Stub"],
        ["", "", "EX-4", "Phase 2", "", "T", "XL", "", "Dissolved", "None"],
        ["", "", "EX-5", "Phase 1", "", "T", "M-L", "", "Superseded", "None"],
        [4, 4, "EX-6", "Phase 1", "", "T", "XS", "", "In Flight", "Draft"],
        [5, 5, "EX-7", "Phase 1", "", "T", "S", "", "Pivot", "Stub"],
    ]
    for r in rows:
        cat.append(r)
    wb.save(path)


def test_recalc_v2_dashboard(tmp_path):
    p = str(tmp_path / "q.xlsx")
    _make_workbook(p)
    subprocess.run([sys.executable, os.path.join(HERE, "recalc.py"), p], check=True)
    d = load_workbook(p)["Dashboard"]
    # Pipeline
    assert d["B11"].value == 7      # total (non-empty Sprint Code)
    assert d["B12"].value == 1      # Completed* wildcard
    assert d["B13"].value == 1      # Blocked
    assert d["B14"].value == 1      # Queued
    assert d["B15"].value == 1      # In Flight
    assert d["B16"].value == 1      # Dissolved
    assert d["B17"].value == 1      # Superseded
    assert round(d["B18"].value, 3) == 0.2           # 1 / (7-1-1)
    # Effort: not-done pts = S1 + M3 + L8 + XS0.5 = 12.5 ; completed pts = S1 = 1
    assert d["B21"].value == 12.5
    assert d["B22"].value == 1
    assert d["B23"].value == 13.5
    assert round(d["B24"].value, 4) == round(1 / 13.5, 4)
    assert d["B25"].value == 3      # blocked+queued+inflight
    # Helper table samples
    assert d["G14"].value == 1      # S remaining pts (EX-7 Pivot)
    assert d["H14"].value == 1      # S completed pts (EX-2)
    assert d["G18"].value == 8      # L remaining pts (EX-3)
    # Status distribution
    assert [d[c].value for c in ("E23", "E24", "E25", "E26", "E27")] == [1, 1, 1, 1, 1]
