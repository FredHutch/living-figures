from typing import Union
import numpy as np
import widgets.streamlit as wist
from living_figures.bio.fom.widgets.microbiome.base_plots import MicrobiomePlot
import pandas as pd
import plotly.express as px
from scipy.spatial import distance
from scipy import stats
import streamlit as st
from living_figures.helpers.constants import tax_levels


class BetaDiversity(MicrobiomePlot):

    label = "Beta Diversity"

    children = [
        wist.StExpander(
            id="options",
            children=[
                wist.StColumns(
                    id="row1",
                    children=[
                        wist.StSelectString(
                            id='metric',
                            label="Distance Metric",
                            options=[
                                'Bray-Curtis',
                                'Euclidean',
                                'Jensen-Shannon'
                            ],
                            value='Bray-Curtis'
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
                        wist.StSelectString(
                            id="color_by",
                            label="Compare Samples By",
                            options=[],
                            value=None
                        )
                    ]
                ),
                wist.StColumns(
                    id="row3",
                    children=[
                        wist.StInteger(
                            id="nbins",
                            label="Number of Bins",
                            min_value=5,
                            max_value=100,
                            value=20
                        ),
                        wist.StResource()
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
        wist.StResource(id="ord_msg"),
        wist.StResource(id="legend_display")
    ]

    @st.cache_data(max_entries=10)
    def get_distances(
        _self,
        abund: pd.DataFrame,
        sample_annots: pd.DataFrame,
        color_by: Union[None, str],
        metric: str
    ) -> str:
        """Compare samples on the basis of a metadata annotation."""

        # Compute the distance matrix
        dm = _self.make_dm(
            abund / abund.sum(),
            metric.replace("-", "").lower()
        )

        # If a comparison metric was selected
        if color_by is not None:

            # Get the metadata category to use for comparison
            meta = sample_annots[color_by].dropna()

            # Filter the distances to just those samples with
            # valid metadata
            dm = dm.reindex(
                index=meta.index.values,
                columns=meta.index.values
            )

        # Melt it into long format
        dm = _self.melt_dm(dm)

        # If a comparison metric was selected
        if color_by is not None:

            # Add a label for that comparison
            if self._root()._is_numeric(sample_annots[color_by]):
                comparison_values = dm.apply(
                    lambda r: _self.delta_meta(
                        r, sample_annots[color_by]
                    ),
                    axis=1
                )
                if comparison_values.apply(
                    lambda v: v in [0., 1.]
                ).all():
                    comparison_values = comparison_values.apply(
                        {
                            0.: "Same",
                            1.: "Different"
                        }.get
                    )
            else:
                comparison_values = dm.apply(
                    lambda r: _self.label_meta(
                        r, sample_annots[color_by]
                    ),
                    axis=1
                )

            dm = dm.assign(
                **{color_by: comparison_values}
            )

        # Return the melted the distance matrix
        return dm

    def delta_meta(self, r, meta):
        """
        Format a label describing the samples being compared
        in terms of their associated metadata values.
        """

        return np.abs(meta[r['index']] - meta[r['variable']])

    def label_meta(self, r, meta):
        """
        Format a label describing the samples being compared
        in terms of their associated metadata values.
        """

        minlabel = min(meta[r['index']], meta[r['variable']])
        maxlabel = max(meta[r['index']], meta[r['variable']])

        if minlabel == maxlabel:
            return f"Within {minlabel}"
        else:
            return f"{minlabel} vs. {maxlabel}"

    @st.cache_data(max_entries=10)
    def make_dm(
        _self,
        abund: pd.DataFrame,
        metric
    ):
        """Make a distance matrix"""

        return pd.DataFrame(
            distance.squareform(
                distance.pdist(
                    abund.T,
                    metric=metric
                )
            ),
            index=abund.columns,
            columns=abund.columns
        )

    @st.cache_data(max_entries=10)
    def melt_dm(
        _self,
        dm: pd.DataFrame
    ):
        """Melt a distance matrix"""

        return dm.reset_index().melt(
            id_vars=["index"],
            value_name="value"
        ).query(
            "index < variable"
        )

    def compare_beta_div_numeric(
        _self,
        dm_long: pd.DataFrame,
        meta: pd.Series
    ) -> str:

        # Compute the difference in metadata value for each
        dm_long = dm_long.assign(
            delta=dm_long.apply(
                lambda r: meta[r['index']] - meta[r['variable']],
                axis=1
            ).abs()
        )

        return stats.spearmanr(dm_long['value'], dm_long['delta'])

    def compare_beta_div_categorical(
        _self,
        dm_long: pd.DataFrame,
        meta: pd.Series
    ) -> str:

        # Assign each comparison as being within vs. between groups
        dm_long = dm_long.assign(
            category=dm_long.apply(
                lambda r: f"Within {meta[r['index']]}" if meta[r['index']] == meta[r['variable']] else "Between Groups", # noqa
                axis=1
            ),
            is_same=lambda d: d["category"] == "Between Groups"
        )

        # Test if the distances are different within vs. between groups
        grouped_vals = {
            is_same: groupvals["value"].tolist()
            for is_same, groupvals in dm_long.groupby(dm_long["is_same"])
        }
        r = stats.mannwhitneyu(
            grouped_vals[True],
            grouped_vals[False],
            alternative="less"
        )

        return r

    def run_self(self) -> None:

        # Get all of the plotting parameters
        params = self.all_values(flatten=True)

        # Get the abundances, filtering to the specified taxonomic level
        # Columns are samples, rows are organisms
        abund: pd.DataFrame = self._root().abund(
            level=params["tax_level"],
            filter=params["filter_by"]
        )

        # Get the sample annotations
        sample_annots = self._root().sample_annotations()

        if abund is None:
            msg = "No abundances found at {tax_level} with {filter_by}"
            msg = msg.format(**params)
            fig = None

        else:

            fig = self.build_fig(
                abund,
                sample_annots,
                params["color_by"],
                params["title"],
                params["metric"],
                params["nbins"]
            )
            msg = None

        if msg is not None and len(msg) > 0:
            self._get_child("ord_msg").main_empty.write(msg)
        if fig is None:
            return

        # Add the plot to the display
        self._get_child("plot").main_empty.plotly_chart(fig)

        # If there is a legend
        if params['legend'] is not None:
            self._get_child(
                "legend_display"
            ).main_empty.markdown(
                params['legend']
            )

    @st.cache_data(max_entries=10)
    def build_fig(
        _self,
        abund,
        sample_annots,
        color_by,
        title,
        metric,
        nbins
    ):

        # Mark the null comparison as a null value
        if color_by == 'None':
            color_by = None

        # Get the beta diversity data
        plot_df = _self.get_distances(
            abund,
            sample_annots,
            color_by,
            metric
        ).dropna()

        # Set up the data which will be used to build the plot
        plot_data = dict(
            data_frame=plot_df,
            y="value",
            nbins=nbins
        )
        plot_f = px.histogram
        layout = dict(
            xaxis_title="Num. Comparisons",
            yaxis_title=f"{metric} Distance"
        )

        # If a comparison was selected
        if color_by is not None:

            # If the value is numeric
            if self._root()._is_numeric(plot_df[color_by]):
                # Make a scatterplot
                plot_f = px.scatter
                # With the x-axis as the metadata
                plot_data["x"] = color_by
                # Label the x axis
                layout["xaxis_title"] = color_by
                # Add a marginal histogram
                plot_data["marginal_y"] = "histogram"
                del plot_data["nbins"]

            # If the value is categorical
            else:
                # Make a facet column
                plot_data["facet_col"] = color_by

                # Add the yaxis title for all subplots
                for i in range(
                    plot_data["data_frame"][color_by].unique().shape[0]
                ):
                    axis_name = 'xaxis' if i == 0 else f'xaxis{i+1}'
                    if axis_name not in layout:
                        layout[axis_name] = dict()
                    layout[axis_name]['title'] = ""

        # Make a plot
        fig = plot_f(**plot_data)
        fig.update_layout(**layout)

        if plot_data.get("facet_col") is not None:
            fig.update_xaxes(matches=None)

        if color_by is not None:
            fig.for_each_annotation(
                lambda a: a.update(text=a.text.split("=")[-1])
            )

        # If there is a title
        if title is not None and title != "None":
            fig.update_layout(title=title)

        return fig
