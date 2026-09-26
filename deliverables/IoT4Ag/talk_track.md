# Three-minute talk track

## Slide 1

Our crop team has two decisions: which plots deserve a visit now, and which hybrids deserve the next trial. FieldSignal connects those decisions using agronomic records and satellite observations. We studied 84 hybrids and 2,131 plots across five Nebraska and Iowa locations. This is a 2022 historical replay. Our forecasts are tested at locations withheld from training, while our hybrid shortlist is separately labeled as observed harvest evidence.

## Slide 2

What does imagery add? We held the plots, site folds and model settings constant. At day 75, agronomic records found 24 low-yield plots in 50 visits. Adding imagery found 30: six additional useful inspections. That is 60 percent precision, but only seven percent recall of all 428 low-yield plots. Nitrogen alone found six, although tied predictions make that comparison sensitive to plot ordering. Combined yield error was 45.5 bushels per acre, compared with 55.1 for the training mean.

## Slide 3

The candidate warning rule is explicit. Starting at day 75, flag the lowest predicted fifth within each site, then inspect in priority order up to capacity. The screen found 163 of 428 eventual low-yield plots. In Ames, priority one was correctly reached. A very low-yield plot ranked thirteenth: it was flagged, but ten visits would miss it. Day 90 reduced yield error, yet screen recall fell. Scouts must establish the cause; the model does not diagnose stress or prescribe treatment.

## Slide 4

For the next trials, we keep observed findings separate from forecasts. We average replicates within treatments and weight sites equally. These five candidates exceed the median at every site; the weakest-site column prevents a strong average from hiding poor performance. They are promising in the observed environments, not proven across seasons. Management also varies: matched nitrogen contrasts range from minus 23.6 to plus 29.2 bushels per acre across four sites. Field placement may contribute, so these are not fertilizer recommendations.

## Slide 5

At day 90, combined CatBoost reaches 44 bushels per acre error, about twenty percent below the training mean, and recovers 4.6 of the observed top ten hybrids per site. Exploratory Ridge improves those figures, but site bias and ranking failures remain. We have demonstrated spatial transfer in 2022, not cross-season reliability or guaranteed yield gains. Our proposal is concrete: use the shortlist to prioritize replicated trials, record what scouts find, freeze the pipeline, and test it on untouched 2023 data.