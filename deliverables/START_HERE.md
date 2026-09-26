# FieldSignal hackathon package

## Current IoT4Ag scope — start here

Use **`IoT4Ag/FieldSignal_IoT4Ag_pitch.pptx`** for the current five-slide presentation and **`IoT4Ag/FieldSignal_IoT4Ag_brief.pdf`** as the one-page handout. `IoT4Ag/FieldSignal_scope_and_demo.md` compiles the scope, evidence, demo sequence, limitations and judge Q&A. Speaker notes and `IoT4Ag/talk_track.md` contain the three-minute narration. `IoT4Ag/tables/` and `IoT4Ag/figures/` contain reusable evidence.

The current dashboard opens **Decision brief**: day 75, Ames, 10 trial plots. Show the inspection list, then the imagery comparison and observed shortlist. The pitch connects scouting today to hybrid selection for the next replicated trials. It claims 2022 spatial transfer only; 2023 is the next test.

The material below describes the earlier hybrid-focused presentation, retained as supporting background.

**Positioning:** Satellite-informed forecasts for better hybrid selection across environments.

## Present

1. Open `FieldSignal_pitch.pptx`. It contains exactly five slides, editable evidence charts, and speaker notes.
2. Rehearse `FieldSignal_talk_track.md` at roughly 150 words per minute for a three-minute pitch.
3. Share `FieldSignal_findings.pdf` as the one-page handout. The Markdown version is available for copy edits.

## Demonstrate

Open the local dashboard at http://127.0.0.1:8501 while the project server is running.

- Start with **Observed harvest (2022)** and show the shortlist's performance at all five sites.
- Open **Management response** to show why the mean nitrogen contrast alone is insufficient.
- Switch to **Forecast (held-out sites)** and explain that these rankings use predictions made without that site's harvest labels.
- Use **Forecast evidence** to show both yield error and recovery of the observed top 10. Keep weak site results visible.
- Scouting remains available as a secondary workspace.

## Supported headlines

- All five observed shortlisted hybrids exceed the median at every site. The leader, HOEGEMEYER 8065RR, averages the 93.4th percentile and has a weakest-site percentile of 84.3.
- Observed 150-minus-75 lb N/acre contrasts range from -23.6 to +29.2 bu/ac across four sites, based on 336 matched hybrid-site pairs.
- At day 90, exploratory Ridge with imagery has MAE of 39.4 bu/ac, versus 55.1 for the training-mean baseline. It recovers 5.0 of the observed top 10 hybrids per site on average, compared with random expectation of 1.19.

These are 2022 results across five sites. Do not describe them as cross-season validation, guaranteed yield gains, isolated irrigation effects, or optimal fertilizer prescriptions. The observed shortlist is not a forecast. Forecasts are useful but imperfect.

## Evidence and reusable files

`figures/` contains three figures, each in PNG and SVG. `tables/` contains observed and forecast comparisons, matched nitrogen contrasts, model metrics, and Ridge predictions. `claims.json` is the numerical claim registry used by the presentation materials.

The original dataset and executable pipeline stay in the Hackathon project; they are not included in this presentation package. Full provenance and Ridge fold audits are in `outputs/broad_performance/` in that project. The standalone package works without a live dashboard.
