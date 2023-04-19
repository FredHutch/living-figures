# Feature and Observation Matrix (FOM)

Collection of visualization utilities which can be used to analyze
datasets which consist of a group of observations (or 'samples') that
have been measured in terms of a set of features.

Examples of this type of dataset include gene expression (RNAseq)
microbiome composition (16S/WGS), and many more.

## Input Data

### Feature Abundance

The data tables used to drive these visualizations are considered
to be organized with each sample's data in a single column, while
each row corresponds to a single feature.
The first row in the dataset contains the sample identifiers,
while the first column contains the feature identifiers.

### Sample / Feature Annotations

Some of the sample composition analysis tools allow for the user
to provide metadata for samples and/or features.
In those sample or feature annotation tables the first column
contains the sample/feature identifier, and the first row contains
the label which is assigned to each metadata attribute.

## Utilities

In the `utilities/` subfolder, objects which are useful across multiple
different types of FOM data.

## Widgets

In the `widgets/` subfolder is a collection of widgets which use
FOM data in some way.
