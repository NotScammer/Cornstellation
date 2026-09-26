# Crop performance, aerial, and satellite data from multistate maize yield trials

[https://doi.org/10.5061/dryad.905qftttm](https://doi.org/10.5061/dryad.905qftttm)

Maize (*Zea mays*) field experiments were conducted at five locations in 2022: Scottsbluff, NE, Lincoln, NE, Missouri Valley, IA, and Ames, IA  with two-thirds of the experiment in one field and one-third of the experiment in another field and Crawfordsville, IA.

This file describes the organization and format of the satellite, UAV, and ground truth data published in Shrestha et al. In addition, we provide an example code for searching and retrieving images from individual hybrid corn research plots as well as calculating the wavelength intensity values and indices employed in our study.

## Directory Layout:

*   **Satellite**
    *   Five directories correspond to five of the six locations from which satellite imagery was collected (North Platte, NE was excluded because of issues with plot segmentation).
    *   Six directories numbered sequentially "TP1", "TP2", "TP3", "TP4", "TP5", and "TP6" corresponding to the order of satellite images collected at each location. Note that the timing of time points with the same number are not identical across locations, and are not guaranteed to be similar. The time of acquisition for each time point at each location is provided in the file **DateofCollection.xlsx** in the folder **"GroundTruth"**.
    *   .TIF formatted images segmented for each plot at a given location at a given time point. Rows often were at orientations other than 0 or 90 degrees in satellite images. Segmented images consist of the minimum bounding box encompassing the plot of interest, with real pixel data for all plot pixels and zero values entered for all pixels within the minimum bounding box but not part of the plot of interest.
    *   Plot image names follow the format location-time-experiment_range_row.tif (Lincoln-TP1-hybirds_2_2.TIF). An example implementation of how to map between image names, plot IDs, and ground truth information is provided later in this document. The necessary information to map between ground truth, plot ID, and images is provided in the file **HYBRID_HIPS_V3.5_ALLPLOTS.csv** located in the **"GroundTruth"** folder.
    *   Each image contains data on six bands per pixel: near-infrared, red edge, red, green, blue, and deep blue.
    *   **FieldLevelImages** contains field level images before cropping/segmenting to produce plot level images with copyright attribution **© Airbus DS (2022)**. .PNG formatted images names follow location-time-experiment.PNG (Lincoln-TP1-hybrids.PNG).
*   **UAV**
    *   Five directories corresponding to five of the six locations from which UAV imagery was collected (as with the satellite images, North Platte, NE UAV images were excluded because of issues with plot segmentation).
    *   Three directories numbered sequentially "TP1", "TP2", and "TP3" corresponding to the order of UAV flights conducted at each location. Note that the timing of time points with the same number is not identical, and is not guaranteed to be similar across locations. The time of acquisition for each time point at each location is provided in the file **DateofCollection.xlsx** in folder **"GroundTruth"**.
    *   .PNG formatted images segmented for each plot at a given location at a given time point. Rows often were at orientations other than 0 or 90 degrees in UAV image mosaics. Segmented images consist of the minimum bounding box encompassing the plot of interest, with real pixel data for all plot pixels and zero values entered for all pixels within the minimum bounding box but not part of the plot of interest.
    *   Plot image names follow the format location-time-experiment_range_row.png (Crawfordsville-TP1-4351_3_15.PNG). An example implementation of how to map between image names, plot IDs, and ground truth information is provided later in this document. The necessary information to map between ground truth, plot ID, and images is provided in the file **HYBRID_HIPS_V3.5_ALLPLOTS.csv** located in the **"GroundTruth"** folder.
    *   Each image contains data on three bands per pixel: red, green, and blue.
*   **GroundTruth**
    *   **HYBRID_HIPS_V3.5_ALLPLOTS.csv** contains one record per hybrid maize plot grown at each of the six locations in this study. Each record includes information on the field, location within the field (row and column), the hybrid genotype planted in that plot, and a set of ground truth data collected from that plot. The individual ground truth measurements are defined below
        *   plantingDate: the date the plot was planted.
        *   totalStandCount: The number of living plants observed in the middle two rows of the four-row plot. Note that plots are variable length between locations, so this needs to be corrected for plot size to calculate the density of plants per unit area.
        *   daysToAnthesis: The difference between the planting date and the first date where at least 50% of living plants in the plot had visible anthers present on their tassels (syn. "male flowering"). Not present for all locations.
        *   GDDToAnthesis: This is a method for quantifying flowering time that corrects for the fact plants grow faster on warm days and slower in the cold. GDD stands for growing degree days. The number of growing degree days per day was calculated using temperatures in Fahrenheit with a crop base temperature of 50 degrees and a crop maximum temperature of 86 degrees.
        *   yieldPerAcre: estimated grain yield per plot. This measurement starts with the direct measurement of grain pass per plot and grain moisture percentage and then corrects for variation in moisture content and differences in plot size across locations to calculate bushels per acre yield at a standardized 15.5% moisture content.
    *   **DateofCollection.xlsx** translates location + TP1/2/3/etc into the specific date of image collection for both UAV and Satellite images collected at all locations included in this study.
*   **Documentation**
    *   Documentation.ipynb: example code for extracting images, calculating different indices, and linking images/indices to the ground truth data.
    *   Readme.md: explaination of data types and layout.