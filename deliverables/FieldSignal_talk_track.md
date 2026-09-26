## Slide 1

A research team needs to choose which hybrids deserve another round of trials. The highest yield at one location is only part of that decision. FieldSignal compares the same 84 hybrids across five Nebraska and Iowa locations, using 2,131 labeled plots and satellite observations. We separate two questions: which hybrids performed consistently in the completed trials, and how well imagery can forecast their performance at a location the model has never seen. Today, our evidence covers 2022.

## Slide 2

The environment changes the yield picture dramatically. Balanced site means range from about 41 to 165 bushels per acre. We therefore avoid ranking hybrids using pooled plot averages. First, we average their replicates inside each treatment. Then we compare hybrids with peers in the same environment, average treatment percentiles within a site, and give each site equal weight. This prevents a favorable location or a frequently repeated control hybrid from dominating the shortlist. It describes relative trial performance, not a causal genetic effect.

## Slide 3

This is the observed shortlist, not a model-generated claim. All five candidates are above the median at every site. HOEGEMEYER 8065RR leads with an average percentile of 93.4 and a weakest-site percentile of 84.3. The table makes the trade-off visible: a high average does not necessarily mean uniform performance. Our rule requires above-median results at at least four sites, then ranks by the equal-site average. We retain replicate counts because some treatment cells have only one plot. These candidates warrant further replicated trials, not a claim of proven adaptation across seasons.

## Slide 4

Management responses also depend on the environment. We matched 84 hybrids at two nitrogen rates within each of four locations, giving 336 hybrid-site comparisons. The observed difference ranges from -23.6 bushels per acre at Ames to plus 29.2 at Scottsbluff. The equal-site mean is plus 8.0, but that single number hides the variation. Because treatments can occupy separate experiments, these are descriptive contrasts rather than fertilizer prescriptions. Missouri Valley has only one rate, and irrigation is site-associated, so neither supports an independent dose or irrigation effect.

## Slide 5

We tested forecasting by withholding each location entirely. At day 90, the training-mean baseline has an error of 55.1 bushels per acre. CatBoost with imagery reaches 44.0, and our exploratory Ridge comparison reaches 39.4. Yield error alone is insufficient for hybrid selection. Ridge recovers 5.0 of the observed top ten hybrids per site on average, compared with 4.6 for CatBoost and about 1.2 expected at random. This is useful but imperfect evidence. Our proposal is to advance the observed shortlist into replicated trials and validate the frozen forecasting pipeline on 2023 before claiming cross-season reliability.