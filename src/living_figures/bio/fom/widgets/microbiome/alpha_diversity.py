from scipy.stats import entropy, spearmanr, pearsonr
import streamlit as st
from typing import Union
from living_figures.bio.fom.widgets.microbiome.base_plots import MicrobiomePlot
from living_figures.helpers.constants import tax_levels
from living_figures.helpers.parse_numeric import is_numeric
import widgets.streamlit as wist
import pandas as pd
import plotly.express as px


class AlphaDiversity(MicrobiomePlot):
    """
    Display the alpha diversity of each sample, summarizing the complexity
    of the mixture of organisms which is present.

    Options:
        - Diversity metric (e.g. Shannon, Simpsons)
        - Taxonomic level
        - Filter samples
        - Display form:
            * Bars
            * Points
            * Distribution
        - Group by metadata
        - Figure height
        - Title
        - Legend
    """

    label = "Alpha Diversity"

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
                            options=[
                                'Distribution',
                                'Points',
                                'Bars'
                            ],
                            value='Distribution'
                        ),
                        wist.StSelectString(
                            id="tax_level",
                            label="Taxonomic Level",
                            options=tax_levels,
                            value="genus"
                        )
                    ]
                ),
                wist.StColumns(
                    id="row2",
                    children=[
                        wist.StSelectString(
                            id="filter_by",
                            label="Filter Samples",
                            options=[],
                            value=None
                        ),
                        wist.StSelectString(
                            id="color_by",
                            label="Compare Samples By",
                            options=[]
                        )
                    ]
                ),
                wist.StColumns(
                    id='row3',
                    children=[
                        wist.StSelectString(
                            id="metric",
                            label="Diversity Metric",
                            options=[
                                "Shannon",
                                "Simpson"
                            ],
                            value="Shannon"
                        ),
                        wist.StInteger(
                            label="Figure Height",
                            id="figure_height",
                            min_value=100,
                            max_value=1200,
                            step=1,
                            value=600
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

    def get_alpha_diversity(_self, **kwargs) -> Union[None, pd.DataFrame]:
        """Return a table with the alpha diversity metrics for each sample."""

        # Get the abundances
        abund = _self._root().abund(
            level=_self.val("tax_level"),
            filter=_self.val("filter_by")
        )

        # If there are no abundances
        if abund is None:
            return

        # Calculate the selected alpha diversity
        metric = _self.val('metric')
        if metric == "Shannon":
            adiv = _self.calc_shannon(abund)
        else:
            msg = f"Unrecognized metric = '{metric}"
            assert metric == "Simpson", msg
            adiv = _self.calc_simpson(abund)

        return adiv

    def calc_shannon(self, abund: pd.DataFrame):
        """Calculate Shannon diversity"""

        return pd.DataFrame(
            dict(Shannon=(abund / abund.sum()).apply(entropy))
        )

    def calc_simpson(self, abund: pd.DataFrame):
        """Calculate Simpson diversity"""

        return pd.DataFrame(
            dict(
                Simpson=(
                    abund / abund.sum()
                ).apply(
                    lambda c: 1 / c.apply(lambda v: v**2 if v > 0 else 0).sum()
                )
            )
        )

    def run_self(self):

        # Get all of the ploting parameters
        kwargs = self.all_values(flatten=True)
        kwargs['abund_hash'] = self._root().abund_hash()
        kwargs['annot_hash'] = self._root().annot_hash()

        # Compute the alpha diversity table
        adiv = self.calc_adiv(
            **{
                kw: kwargs[kw]
                for kw in [
                    'abund_hash',
                    'annot_hash',
                    'tax_level',
                    'filter_by',
                    'metric'
                ]
            }
        )

        if adiv is None:
            return

        # Get the plot
        fig = self.make_fig(
            adiv,
            **{
                kw: val
                for kw, val in self.all_values(flatten=True).items()
                if kw not in ['legend']
            }
        )

        # Show the plot
        self.option("plot").main_empty.plotly_chart(fig)

        # Print any correlation metrics
        corr_msg = self.report_corr(adiv, kwargs['metric'], kwargs['color_by'])
        if corr_msg is not None:
            self.option("plot_msg").main_empty.write(corr_msg)

    # @st.cache_data
    def report_corr(_self, adiv, metric, color_by):
        """Print any correlation metrics."""

        if color_by is None or color_by == 'None':
            return

        stats_df = adiv.reindex(
            columns=[metric, color_by]
        ).dropna()

        if is_numeric(stats_df[color_by]):
            return _self.spearman(stats_df, metric, color_by)
        else:
            return _self.anova(stats_df, metric, color_by)

    @st.cache_data(max_entries=10)
    def calc_adiv(_self, **kwargs) -> Union[None, pd.DataFrame]:
        """Make the primary figure for plotting."""

        # Get the alpha diversity of the samples which were uploaded
        adiv = _self.get_alpha_diversity(**kwargs)

        # If there is no data
        if adiv is None:
            # Take no action
            return

        # If there is sample metadata
        annot_df = _self._root().sample_annotations()
        if annot_df is not None:

            # Add it to the plotting table
            adiv = pd.merge(
                adiv,
                annot_df,
                left_index=True,
                right_index=True,
                how="left"
            )

        return adiv

    @st.cache_data(max_entries=10)
    def make_fig(_self, adiv, **kwargs):
        """Make the primary figure for plotting."""

        # Make the plot
        if kwargs["plot_type"] == "Distribution":
            fig = _self.plot_distribution(adiv)
        elif kwargs["plot_type"] == "Points":
            fig = _self.plot_points(adiv)
        elif kwargs["plot_type"] == "Bars":
            fig = _self.plot_bars(adiv)
        else:
            msg = f"Unrecognized plot type {kwargs['plot_type']}"
            _self.option("plot_msg").main_empty.write(msg)
            return

        if kwargs["title"] is not None and kwargs["title"] != "None":
            fig.update_layout(title=kwargs["title"])

        return fig

    def plot_distribution(self, adiv: pd.DataFrame):

        plot_data = dict(
            data_frame=adiv,
            x=self.val("metric")
        )
        layout = dict(
            yaxis_title="Number of Samples"
        )

        plot_f = px.histogram

        # If there is a grouping
        color_by = self.val("color_by")
        if color_by is not None and color_by != 'None':

            # Only show samples which have the metadata assigned
            plot_data["data_frame"] = plot_data["data_frame"].reindex(
                columns=[
                    self.val("metric"),
                    color_by
                ]
            ).dropna()

            # If the value is numeric
            if is_numeric(adiv[color_by]):
                # Make a scatterplot
                plot_f = px.scatter
                # With the y-axis as the metadata
                plot_data["y"] = color_by
                # Label the y axis
                layout["yaxis_title"] = color_by

            # If the value is categorical
            else:
                # Make a facet row
                plot_data["facet_row"] = color_by

        fig = plot_f(**plot_data)
        fig.update_layout(
            **layout
        )

        return fig

    def spearman(self, adiv: pd.DataFrame, metric: str, color_by: str) -> None:

        r = spearmanr(
            adiv[metric].tolist(),
            adiv[color_by].apply(float).tolist(),
        )
        msg = " ".join([
            "Spearman:",
            f"statistic={r.statistic:.2g},",
            f"p={r.pvalue:.2g}"
        ])

        r = pearsonr(
            adiv[metric].tolist(),
            adiv[color_by].apply(float).tolist(),
        )
        msg = msg + "  \n" + " ".join([
            "Pearson:",
            f"statistic={r.statistic:.2g},",
            f"p={r.pvalue:.2g}"
        ])

        return msg

    def anova(
        self,
        adiv: pd.DataFrame,
        metric: str,
        color_by: str
    ) -> None:

        print(color_by)
        print(metric)
        print(adiv)
