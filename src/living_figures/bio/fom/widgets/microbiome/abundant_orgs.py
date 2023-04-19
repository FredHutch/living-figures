from typing import Union
from living_figures.helpers.sorting import sort_table
import widgets.streamlit as wist
from living_figures.bio.fom.widgets.microbiome.base_plots import MicrobiomePlot
from widgets.base.exceptions import WidgetFunctionException
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from living_figures.helpers.constants import tax_levels


class AbundantOrgs(MicrobiomePlot):

    label = "Abundant Organisms"

    children = [
        wist.StExpander(
            id="options",
            expanded=True,
            children=[
                wist.StColumns(
                    id="row1",
                    children=[
                        wist.StSelectString(
                            id='plot_type',
                            label="Plot Type",
                            options=['Heatmap', 'Stacked Bars'],
                            value='Heatmap'
                        ),
                        wist.StSelectString(
                            id="tax_level",
                            label="Taxonomic Level",
                            options=tax_levels,
                            value="class"
                        )
                    ]
                ),
                wist.StColumns(
                    id="row2",
                    children=[
                        wist.StSelectString(
                            id="filter_by",
                            label="Filter Samples By",
                            options=[],
                            value=None
                        ),
                        wist.StMultiSelect(
                            id="color_by",
                            label="Color Samples By",
                            options=[],
                            value=[]
                        )
                    ]
                ),
                wist.StColumns(
                    id='row3',
                    children=[
                        wist.StInteger(
                            id="n_orgs",
                            label="Max # of Organisms",
                            min_value=2,
                            max_value=100,
                            value=10
                        ),
                        wist.StSelectString(
                            id="sort_by",
                            label="Sort Samples By",
                            options=[
                                "Organism Abundances",
                                "Selected Metadata",
                                "Input Order"
                            ]
                        )
                    ]
                ),
                wist.StColumns(
                    id="row4",
                    children=[
                        wist.StString(id='title'),
                        wist.StTextArea(id='legend')
                    ]
                )
            ]
        ),
        wist.StResource(id="plot"),
        wist.StResource(id="plot_msg"),
        wist.StResource(id="legend_display")
    ]

    def get_abundance_data(self):

        # Get the plotting options
        params = self.all_values(flatten=True)

        # Get the abundances, filtering to the specified taxonomic level
        # Columns are samples, rows are organisms
        abund: pd.DataFrame = self._root().abund(
            level=params['tax_level'],
            filter=params['filter_by']
        )

        if abund is None:
            return

        # If there are no more organisms than the specified max
        if abund.shape[0] <= params["n_orgs"]:
            return abund

        # Otherwise, we need to filter down the number of organisms being shown

        # Compute the average abundance of each organism
        mean_abund = abund.mean(axis=1).sort_values(ascending=False)

        to_keep = mean_abund.index.values[:(params["n_orgs"]-1)]

        abund = pd.concat([
            abund.reindex(index=to_keep),
            pd.DataFrame(dict(
                Other=abund.drop(index=to_keep).sum()
            )).T
        ])

        return abund

    def run_self(self):

        # Get the abundance data to plot
        abund_df = self.get_abundance_data()
        if abund_df is None:
            return

        # Get the metadata (if any was provided)
        sample_annots: pd.DataFrame = self._root().sample_annotations()

        # Get the coloring column
        color_by = self.option("color_by").get_value()

        # If there is metadata and the user wants to display it
        if len(color_by) > 0 and sample_annots is not None:

            annot_df = sample_annots.reindex(
                columns=color_by,
                index=abund_df.columns.values
            )

        else:
            annot_df = None

        # If the user requested to sort samples by organism abundances
        sort_by = self.option("sort_by").get_value()
        if sort_by == "Organism Abundances":

            # Sort the abundance table
            abund_df = sort_table(abund_df)

            # Order the annotations to match
            if annot_df is not None:
                annot_df = annot_df.reindex(index=abund_df.columns.values)

        # If the user requested to sort samples by annotations
        elif sort_by == "Selected Metadata" and annot_df is not None:

            # Sort the annotation table
            annot_df = annot_df.dropna().sort_values(by=annot_df.columns.values)

            # Order the abundances to match
            abund_df = abund_df.reindex(columns=annot_df.index.values)

        self.option("plot").main_empty.write(abund_df)
        self.option("plot").main_empty.write(annot_df)
