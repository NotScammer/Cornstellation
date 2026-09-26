from pathlib import Path
import re
from html import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'deliverables/FieldSignal_model_usefulness.md'
OUTPUT = SOURCE.with_suffix('.pdf')
for name, filename in [('Arial', 'arial.ttf'), ('Arial-Bold', 'arialbd.ttf'), ('Arial-Italic', 'ariali.ttf'), ('Arial-BoldItalic', 'arialbi.ttf')]:
    pdfmetrics.registerFont(TTFont(name, 'C:/Windows/Fonts/' + filename))
pdfmetrics.registerFontFamily('Arial', normal='Arial', bold='Arial-Bold', italic='Arial-Italic', boldItalic='Arial-BoldItalic')
green = colors.HexColor('#173E2C')
muted = colors.HexColor('#546359')
body = ParagraphStyle('body', fontName='Arial', fontSize=10, leading=13.6, textColor=green, spaceAfter=8)
heading = ParagraphStyle('heading', parent=body, fontName='Arial-Bold', fontSize=13, leading=16, spaceBefore=10, spaceAfter=7, keepWithNext=True)
title = ParagraphStyle('title', parent=heading, fontSize=24, leading=28, spaceBefore=0, spaceAfter=12)
small = ParagraphStyle('small', parent=body, fontSize=8.5, leading=11.5)
cell = ParagraphStyle('cell', parent=body, fontSize=9, leading=12, spaceAfter=0)
th = ParagraphStyle('th', parent=cell, fontName='Arial-Bold', textColor=colors.white)
callout = ParagraphStyle('callout', parent=body, backColor=colors.HexColor('#EEF2E8'), borderPadding=8, spaceBefore=4, spaceAfter=12)

def fmt(text):
    text = text.replace('\u2013', '-').replace('\u2014', '-').replace('\u2011', '-').replace('\u2192', 'to')
    text = escape(text)
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    return re.sub(r'`([^`]+)`', r'<font size="8.5">\1</font>', text)

story = []
lines = SOURCE.read_text(encoding='utf-8').splitlines()
i = 0
current_section = ''
while i < len(lines):
    line = lines[i].strip()
    if not line:
        i += 1
        continue
    if line.startswith('# '):
        story.append(Paragraph(fmt(line[2:]), title))
    elif line.startswith('## '):
        current_section = line[3:]
        if current_section.startswith(('3.', '5.')):
            story.append(PageBreak())
        story.append(Paragraph(fmt(current_section), heading))
    elif line.startswith('|'):
        rows = []
        while i < len(lines) and lines[i].strip().startswith('|'):
            values = [x.strip() for x in lines[i].strip().strip('|').split('|')]
            if not all(re.fullmatch(r'[-:]+', x) for x in values):
                rows.append(values)
            i += 1
        n = len(rows[0])
        widths = {2: [295, 233], 3: [264, 132, 132], 4: [168, 105, 105, 150]}[n]
        cells = [[Paragraph(fmt(v), th if row == 0 else cell) for v in values] for row, values in enumerate(rows)]
        table = Table(cells, colWidths=widths, repeatRows=1, hAlign='LEFT')
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), green),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#F0F3EA'), colors.white]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story += [table, Spacer(1, 10)]
        continue
    else:
        paragraph = [line]
        while i + 1 < len(lines) and lines[i + 1].strip() and not lines[i + 1].startswith(('#', '|')):
            i += 1
            paragraph.append(lines[i].strip())
        text = ' '.join(paragraph)
        style = callout if text.startswith('**Decision value:**') or current_section == 'A short pitch' else small if current_section == 'Traceable evidence' else body
        story.append(Paragraph(fmt(text), style))
    i += 1

def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor('#CFD9CA'))
    canvas.line(42, 38, 570, 38)
    canvas.setFillColor(muted)
    canvas.setFont('Arial', 8)
    canvas.drawString(42, 25, 'CORNSTELLATION  /  FIELDSIGNAL  /  FIVE LOCATIONS, 2022')
    canvas.drawRightString(570, 25, str(doc.page))
    canvas.restoreState()

SimpleDocTemplate(str(OUTPUT), pagesize=letter, leftMargin=42, rightMargin=42, topMargin=36, bottomMargin=50,
                  title='FieldSignal: findings and practical value', author='Cornstellation').build(story, onFirstPage=footer, onLaterPages=footer)
pdf = PdfReader(OUTPUT)
print(f'{OUTPUT}: {len(pdf.pages)} pages')
for n, page in enumerate(pdf.pages, 1):
    text = page.extract_text()
    print(n, len(text), text[:90].replace('\n', ' '))
full = '\n'.join(p.extract_text() for p in pdf.pages)
for phrase in ['28.4%', '39.4', 'HOEGEMEYER 8065RR', 'Traceable evidence', 'A short pitch', '0.07']:
    assert phrase in full, phrase
