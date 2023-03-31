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

In the `utilities/` subfolder:

### FOM Selector

To encompass all of the different types of widgets which can be used
to manipulate FOM data, we will create a selector object which is
able to select which of the different widgets is displayed driven by
dropdown menu selection.

### FOM Replicator

To give the user the ability to chain multiple FOM widgets in a
row, we will use a Replicator object to expand/contract a list
of FOM Selector sub-widgets.

## Widgets

In the `widgets/` subfolder is a collection of widgets which use
FOM data in some way.

### Shared Resource Usage

To allow the FOM Widgets to process the same set of data without
duplicating it, there is a shared set of resource naming convention
which is used to access those resources.

Each of these widgets will look for these Resources as part of
their parent ResourceList.
