"""Small static report renderer; report values always come from computed artifacts."""

import html
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def render(out, title, metrics, tables, narrative, chart=None):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(
        json.dumps(metrics, indent=2, allow_nan=False, default=str) + "\n"
    )
    blocks = []
    for name, frame in tables.items():
        frame.to_csv(out / f"{name}.csv", index=False)
        blocks.append(
            f"<h2>{html.escape(name.replace('_', ' ').title())}</h2>"
            + frame.head(30).to_html(
                index=False, escape=True, float_format=lambda x: f"{x:,.3f}"
            )
        )
    if chart:
        labels, values, ylabel = chart
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.bar(labels, values, color="#22b8a8")
        ax.set_ylabel(ylabel)
        ax.tick_params(axis="x", rotation=25)
        fig.tight_layout()
        fig.savefig(out / "chart.svg")
        plt.close(fig)
    cards = "".join(
        f"<article><small>{html.escape(k)}</small><strong>{html.escape(str(v))}</strong></article>"
        for k, v in metrics.items()
        if isinstance(v, (int, float, str))
    )
    page = (
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>'
        + html.escape(title)
        + "</title><style>body{font:16px system-ui;background:#f4f7fa;color:#12243a;max-width:1150px;margin:auto;padding:40px}h1{font-size:40px}.cards{display:flex;flex-wrap:wrap;gap:12px}article{background:white;padding:18px;min-width:180px;border-top:4px solid #22b8a8}strong{display:block;font-size:24px;margin-top:8px}table{border-collapse:collapse;background:white;width:100%;font-size:13px}td,th{padding:9px;border-bottom:1px solid #dce4ec;text-align:left}img{width:100%;background:white;margin-top:24px}.table{overflow:auto}p{line-height:1.6}</style><h1>"
        + html.escape(title)
        + "</h1><p>Synthetic portfolio study • Snapshot 2026-09-30 • No customer data</p><p>"
        + html.escape(narrative)
        + '</p><div class="cards">'
        + cards
        + "</div>"
        + ('<img alt="Analysis chart" src="chart.svg">' if chart else "")
        + "".join('<div class="table">' + b + "</div>" for b in blocks)
        + "</html>"
    )
    (out / "index.html").write_text(page)
