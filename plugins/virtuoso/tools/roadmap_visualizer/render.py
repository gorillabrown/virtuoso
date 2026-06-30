from __future__ import annotations

import json

from .model import PlanningModel, to_jsonable


def render_html(model: PlanningModel) -> str:
    payload = json.dumps(to_jsonable(model), ensure_ascii=True).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Planning Health Cockpit</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #1b1f23;
      --muted: #65717d;
      --line: #d7dde3;
      --panel: #ffffff;
      --page: #f5f7f9;
      --accent: #0f766e;
      --warn: #b45309;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--page);
      color: var(--ink);
      font-family: Arial, Helvetica, sans-serif;
      line-height: 1.45;
    }}
    header {{
      padding: 24px clamp(16px, 4vw, 48px) 16px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }}
    h1 {{ margin: 0 0 8px; font-size: clamp(26px, 4vw, 40px); }}
    .summary {{ margin: 0; color: var(--muted); max-width: 900px; }}
    .tabs {{
      display: flex;
      gap: 8px;
      padding: 16px clamp(16px, 4vw, 48px) 0;
      flex-wrap: wrap;
    }}
    button {{
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--ink);
      border-radius: 6px;
      padding: 8px 12px;
      font: inherit;
      cursor: pointer;
    }}
    button[aria-selected="true"] {{
      background: var(--accent);
      border-color: var(--accent);
      color: white;
    }}
    main {{ padding: 16px clamp(16px, 4vw, 48px) 40px; }}
    section[hidden] {{ display: none; }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }}
    .metric, .notice {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }}
    .metric span {{ display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; }}
    .metric strong {{ display: block; margin-top: 6px; font-size: 26px; }}
    .notice {{ margin-bottom: 16px; }}
    .notice strong {{ color: var(--accent); }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--panel);
      border: 1px solid var(--line);
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }}
    th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; }}
    tr:last-child td {{ border-bottom: 0; }}
    .empty {{ color: var(--muted); font-style: italic; }}
    ul {{ margin: 8px 0 0; padding-left: 20px; }}
  </style>
</head>
<body>
  <header>
    <h1>Planning Health Cockpit</h1>
    <p class="summary">Roadmap sprint queue status, conveyor flow, and dependency alignment in one self-contained report.</p>
  </header>
  <nav class="tabs" aria-label="Planning views">
    <button type="button" data-view="cockpit" aria-selected="true">Cockpit</button>
    <button type="button" data-view="conveyor" aria-selected="false">Conveyor</button>
    <button type="button" data-view="dependencies" aria-selected="false">Dependencies</button>
  </nav>
  <main>
    <section id="cockpit" aria-labelledby="cockpit-title">
      <h2 id="cockpit-title">Cockpit</h2>
      <div class="metrics" id="metrics"></div>
      <div class="notice"><strong>Recommendation</strong><p id="recommendation"></p></div>
      <div class="notice"><strong>Drift Findings</strong><ul id="drift-list"></ul></div>
    </section>
    <section id="conveyor" aria-labelledby="conveyor-title" hidden>
      <h2 id="conveyor-title">Conveyor</h2>
      <table>
        <thead>
          <tr><th>Seq</th><th>Sprint</th><th>Phase / Stage</th><th>LOE</th><th>Implementation</th><th>Written</th></tr>
        </thead>
        <tbody id="conveyor-rows"></tbody>
      </table>
    </section>
    <section id="dependencies" aria-labelledby="dependencies-title" hidden>
      <h2 id="dependencies-title">Dependencies</h2>
      <table>
        <thead>
          <tr><th>Sprint</th><th>Dependency</th></tr>
        </thead>
        <tbody id="dependency-rows"></tbody>
      </table>
    </section>
  </main>
  <script>
    const MODEL = {payload};

    const text = (value) => value === null || value === undefined || value === "" ? "-" : String(value);
    const cell = (value, className = "") => {{
      const td = document.createElement("td");
      td.textContent = text(value);
      if (className) td.className = className;
      return td;
    }};

    function renderMetrics() {{
      const health = MODEL.health || {{}};
      const metrics = [
        ["Head Sprint", health.head_code],
        ["Full-Spec Buffer", health.full_spec_buffer],
        ["Queued", health.queued_count],
        ["In Flight", health.in_flight_count],
        ["Blocked", health.blocked_count],
        ["Drift Findings", health.drift_count],
      ];
      const container = document.getElementById("metrics");
      metrics.forEach(([label, value]) => {{
        const item = document.createElement("div");
        item.className = "metric";
        item.innerHTML = `<span>${{label}}</span><strong></strong>`;
        item.querySelector("strong").textContent = text(value);
        container.appendChild(item);
      }});
      document.getElementById("recommendation").textContent = text(health.recommendation);

      const list = document.getElementById("drift-list");
      const findings = health.drift_findings || [];
      if (!findings.length) {{
        const li = document.createElement("li");
        li.className = "empty";
        li.textContent = "No drift findings.";
        list.appendChild(li);
      }} else {{
        findings.forEach((finding) => {{
          const li = document.createElement("li");
          li.textContent = finding;
          list.appendChild(li);
        }});
      }}
    }}

    function renderConveyor() {{
      const body = document.getElementById("conveyor-rows");
      const rows = MODEL.sprints || [];
      if (!rows.length) {{
        const tr = document.createElement("tr");
        const td = cell("No sprint rows found.", "empty");
        td.colSpan = 6;
        tr.appendChild(td);
        body.appendChild(tr);
        return;
      }}
      rows.forEach((sprint) => {{
        const tr = document.createElement("tr");
        tr.append(
          cell(sprint.seq),
          cell(`${{text(sprint.code)}} - ${{text(sprint.title)}}`),
          cell(`${{text(sprint.phase)}} / ${{text(sprint.stage)}}`),
          cell(sprint.loe),
          cell(sprint.implementation_status),
          cell(sprint.written_status)
        );
        body.appendChild(tr);
      }});
    }}

    function renderDependencies() {{
      const body = document.getElementById("dependency-rows");
      const dependencyRows = [];
      (MODEL.sprints || []).forEach((sprint) => {{
        (sprint.dependencies || []).forEach((dependency) => {{
          dependencyRows.push([sprint.code, dependency]);
        }});
      }});
      if (!dependencyRows.length) {{
        const tr = document.createElement("tr");
        const td = cell("No dependencies recorded.", "empty");
        td.colSpan = 2;
        tr.appendChild(td);
        body.appendChild(tr);
        return;
      }}
      dependencyRows.forEach(([code, dependency]) => {{
        const tr = document.createElement("tr");
        tr.append(cell(code), cell(dependency));
        body.appendChild(tr);
      }});
    }}

    document.querySelectorAll("[data-view]").forEach((button) => {{
      button.addEventListener("click", () => {{
        document.querySelectorAll("[data-view]").forEach((item) => {{
          item.setAttribute("aria-selected", item === button ? "true" : "false");
        }});
        document.querySelectorAll("main section").forEach((section) => {{
          section.hidden = section.id !== button.dataset.view;
        }});
      }});
    }});

    renderMetrics();
    renderConveyor();
    renderDependencies();
  </script>
</body>
</html>
"""
