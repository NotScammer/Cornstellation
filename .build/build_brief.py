"""Create the printable evidence brief from the same claims used by the deck."""
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "outputs/broad_performance"
OUT = ROOT / "deliverables"
c = json.loads((DATA / "claims.json").read_text())
green, muted = colors.HexColor("#173E2C"), colors.HexColor("#556358")
cream = colors.HexColor("#F5F3E9")
body = ParagraphStyle("body", fontName="Helvetica", fontSize=10.2, leading=13.5, textColor=green, spaceAfter=6)
small = ParagraphStyle("small", parent=body, fontSize=8.5, leading=11, textColor=muted)
heading = ParagraphStyle("heading", parent=body, fontName="Helvetica-Bold", fontSize=13, leading=16, spaceBefore=9, spaceAfter=6)
title = ParagraphStyle("title", parent=body, fontName="Helvetica-Bold", fontSize=23, leading=27, spaceAfter=9)
brand = ParagraphStyle("brand", parent=body, fontName="Helvetica-Bold", fontSize=11, leading=15)


def p(text, style=body):
    return Paragraph(text, style)


def table(rows, widths):
    t = Table(rows, colWidths=widths, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.1),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 0), (-1, 0), green),
        ("TEXTCOLOR", (0, 1), (-1, -1), green),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#EDF0E7"), colors.white]),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ]))
    return t


story = [p("FIELDSIGNAL / FINDINGS BRIEF", brand),
         p("Hybrid performance across environments", title),
         p("Satellite-informed forecasts for better hybrid selection across environments."),
         p("2022 trials in Nebraska and Iowa: <b>84 hybrids, five locations, 2,131 labeled plots.</b>"),
         p("Observed shortlist for the next replicated trials", heading),
         p("All five candidates exceed the median at every site. Replicates are averaged within treatment, treatment percentiles within site, and sites equally. These are observed harvest findings, not forecasts.")]
rows = [["Hybrid", "Avg. percentile", "Worst site", "Plots"]]
for h in c["shortlist"]:
    rows.append([h["genotype"], f"{h['average_percentile']:.1f}", f"{h['worst_site_percentile']:.1f}", str(h["replicates"])])
story += [table(rows, [254, 106, 88, 80]), p("Some treatment cells have only one replicate. Shortlist eligibility requires above-median results at four or more sites.", small),
          p("Nitrogen contrasts depend on the site", heading),
          p("Observed 150-minus-75 lb nitrogen/acre differences, matching 84 hybrids within each of four sites:")]
rows = [[r["location"] for r in c["nitrogen_sites"]], [f"{r['mean_difference']:+.1f} bu/ac" for r in c["nitrogen_sites"]]]
story += [table(rows, [132] * 4),
          p(f"The equal-site mean is {c['nitrogen_equal_site_difference']:+.1f} bu/ac across {c['nitrogen_matched_pairs']} matched hybrid-site pairs. Field placement may contribute. These are descriptive contrasts, not optimal-rate recommendations.", small),
          p("Forecast evidence at unseen locations", heading)]
rows = [["Day-90 model", "MAE (bu/ac)", "Top-10 overlap per site"],
        ["Training-mean baseline", f"{c['day90_mean_mae']:.1f}", "Cannot rank hybrids"],
        ["CatBoost with imagery", f"{c['day90_combined_mae']:.1f}", "4.6 of 10"],
        ["Ridge with imagery", f"{c['day90_ridge_combined_mae']:.1f}", "5.0 of 10"]]
story += [table(rows, [238, 115, 175]),
          p(f"Ridge reduces MAE by {c['day90_ridge_improvement_vs_mean_pct']:.1f}% versus the mean baseline. Random top-10 selection has an expected overlap of 1.19. Ridge is exploratory 2022 development with tuning inside training folds; forecasts remain imperfect.", small),
          p("Decision and next test", heading),
          p("Prioritize the observed shortlist for replicated trials. Validate a frozen forecasting pipeline on untouched 2023 data before claiming cross-season reliability."),
          p("Scope: five locations in one season. No causal irrigation effect, guaranteed yield improvement, or financial return is established.", small)]


def page_footer(canvas, doc):
    canvas.setFillColor(muted)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(42, 25, "Evidence: outputs/broad_performance tables and claims.json. Dataset: doi.org/10.5061/dryad.905qftttm")


output = OUT / "FieldSignal_findings.pdf"
SimpleDocTemplate(str(output), pagesize=letter, rightMargin=42, leftMargin=42, topMargin=32, bottomMargin=38,
                  title="FieldSignal: hybrid performance across environments", author="FieldSignal research team").build(story, onFirstPage=page_footer)
reader = PdfReader(output)
assert len(reader.pages) == 1, f"Expected one page; found {len(reader.pages)}"
print(output)
print('One-page PDF verified; render for visual review.')

md = ["# FieldSignal: findings brief", "", "Satellite-informed forecasts for better hybrid selection across environments.", "",
      "2022 only: 84 hybrids, five locations, 2,131 labeled plots.", "", "## Observed shortlist", "",
      "| Hybrid | Average percentile | Worst-site percentile | Plots |", "|---|---:|---:|---:|"]
for h in c["shortlist"]:
    md.append(f"| {h['genotype']} | {h['average_percentile']:.1f} | {h['worst_site_percentile']:.1f} | {h['replicates']} |")
md += ["", "All five exceed the median at every site. Some treatment cells have one replicate. These are observed harvest findings, not forecasts.",
       "", "## Matched nitrogen contrasts", ""]
md += [f"- {r['location']}: {r['mean_difference']:+.1f} bu/ac (150 minus 75 lb N/acre; 84 matched hybrids)." for r in c["nitrogen_sites"]]
md += ["", "Descriptive contrasts, not causal fertilizer or irrigation recommendations.", "", "## Forecast evidence", "",
       f"Day-90 held-out MAE: training mean {c['day90_mean_mae']:.1f}, CatBoost with imagery {c['day90_combined_mae']:.1f}, Ridge with imagery {c['day90_ridge_combined_mae']:.1f} bu/ac.",
       "Ridge recovered 5.0 of the observed top 10 hybrids per site on average; CatBoost recovered 4.6. Random expectation is 1.19.",
       "Ridge comparisons are exploratory development on 2022. No cross-season validation is claimed.", "",
       "Next: advance the observed shortlist to replicated trials and evaluate the frozen forecasting pipeline on 2023."]
(OUT / "FieldSignal_findings.md").write_text("\n".join(md), encoding="utf-8")
