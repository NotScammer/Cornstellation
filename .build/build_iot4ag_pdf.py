"""One-page evidence brief accompanying the IoT4Ag pitch."""
import json
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"deliverables/IoT4Ag"
c=json.loads((ROOT/"outputs/broad_performance/claims.json").read_text())
green=colors.HexColor("#173E2C"); muted=colors.HexColor("#556358")
body=ParagraphStyle("body",fontName="Helvetica",fontSize=9.5,leading=12.3,textColor=green,spaceAfter=5)
small=ParagraphStyle("small",parent=body,fontSize=8,leading=10,textColor=muted)
head=ParagraphStyle("head",parent=body,fontName="Helvetica-Bold",fontSize=12.5,leading=16,spaceBefore=8,spaceAfter=5)
title=ParagraphStyle("title",parent=body,fontName="Helvetica-Bold",fontSize=25,leading=29,spaceAfter=6)
def p(t,s=body): return Paragraph(t,s)
def table(rows,widths):
    t=Table(rows,colWidths=widths,hAlign="LEFT")
    t.setStyle(TableStyle([("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTNAME",(0,1),(-1,-1),"Helvetica"),("FONTSIZE",(0,0),(-1,-1),8.5),("BACKGROUND",(0,0),(-1,0),green),("TEXTCOLOR",(0,0),(-1,0),colors.white),("TEXTCOLOR",(0,1),(-1,-1),green),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.HexColor("#EDF0E7"),colors.white]),("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),("ALIGN",(1,0),(-1,-1),"RIGHT")]))
    return t
story=[p("CORNSTELLATION / IoT4Ag",head),p("FieldSignal: inspect now, trial next",title),p("Satellite-informed forecasts for better hybrid selection across environments."),p("<b>2022 historical replay: 84 hybrids, five locations, 2,131 labeled plots.</b> Nebraska and Iowa. Forecasts withhold each location from training; observed harvest findings are labeled separately.")]
story += [p("1. Imagery improves the inspection list",head),p("At day 75, adding imagery finds <b>six more low-yield plots in 50 visits</b> than agronomic records alone. Each site receives 10 visits. Low yield means the actual bottom 20% within that site.")]
story += [table([["Day-75 inputs","MAE (bu/ac)","Found / 50","Precision"],["Training mean","55.1","7","14%"],["Nitrogen only","59.7","6","12%"],["Agronomic records","72.1","24","48%"],["Agronomy + satellite","45.5","30","60%"]],[242,105,90,91]),p("Same plots and folds; nitrogen, agronomy and combined use identical CatBoost settings. Nitrogen/mean ties use plot ID. The 30 finds represent only 7.0% recall of all 428 low-yield plots.",small)]
story += [p("2. A candidate warning rule with an explicit action",head),p("<b>From day 75, flag the lowest predicted 20% within a site.</b> Rank by predicted yield, then inspect up to capacity. The screen finds 163 of 428 low-yield plots (38.1% precision and recall). Image age and NDVI change provide context; neither is a validated stress threshold."),p("At day 90, combined MAE improves to 44.0 bu/ac and 10 visits/site find 31/50, but 20% screen recall falls to 32.9%. A flag prompts a human check, not a diagnosis or treatment recommendation.",small)]
story += [p("3. Five observed candidates for the next replicated trials",head)]
rows=[["Observed hybrid","Avg. percentile","Weakest site","Plots"]]
for h in c["shortlist"]: rows.append([h["genotype"],f"{h['average_percentile']:.1f}",f"{h['worst_site_percentile']:.1f}",str(h["replicates"])])
story += [table(rows,[242,105,90,91]),p("All five exceed the median at all five sites. Average replicates within treatment, treatment percentiles within site, then weight sites equally. Some treatment cells have only one replicate. These are harvest findings, not forecasts.",small)]
story += [p("Management depends on the environment",head),p("Matched 150-minus-75 lb N/acre contrasts: Ames <b>-23.6</b>, Crawfordsville <b>+15.4</b>, Lincoln <b>+10.9</b>, Scottsbluff <b>+29.2 bu/ac</b>. Equal-site mean: +8.0; 84 matched hybrids/site, 336 pairs. These are observed contrasts; field placement may contribute. No isolated irrigation effect is established.")]
story += [p("The proposal: advance the shortlist, then validate on 2023",head),p("Day-90 combined CatBoost recovers 4.6 of the observed top 10 hybrids per held-out site. Exploratory Ridge reaches 39.4 bu/ac MAE and 5.0/10 overlap. Freeze the pipeline, record scouting outcomes, and evaluate untouched 2023 data before claiming cross-season reliability.")]
def footer(canvas,doc):
    canvas.setFillColor(muted);canvas.setFont("Helvetica",7)
    canvas.drawString(42,24,"Sources: accompanying tables/model_comparison.csv, warning_evaluation.csv, observed_hybrids.csv, nitrogen_sites.csv, ranking_metrics.csv.")
file=OUT/"FieldSignal_IoT4Ag_brief.pdf"
SimpleDocTemplate(str(file),pagesize=letter,leftMargin=42,rightMargin=42,topMargin=25,bottomMargin=35,title="FieldSignal by Cornstellation: IoT4Ag findings",author="Cornstellation").build(story,onFirstPage=footer)
assert len(PdfReader(file).pages)==1
print(file)
