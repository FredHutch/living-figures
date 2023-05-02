import numpy as np
from scipy.stats import spearmanr, f_oneway
from statsmodels.stats.multitest import multipletests
import streamlit as st
from living_figures.bio.fom.widgets.microbiome.base_plots import MicrobiomePlot
from living_figures.helpers.constants import tax_levels
from living_figures.helpers.parse_numeric import is_numeric
import widgets.streamlit as wist
import pandas as pd
import plotly.express as px


class DifferentialAbundance(MicrobiomePlot):
    """
    Identify organisms which are differentially abundant between two
    groups of samples, or in correlation with a continuous metadata variable.
    """

    label = "Differential Abundance"

    children = [
        wist.StExpander(
            id="options",
            children=[
                wist.StColumns(
                    id="row1",
                    children=[
                        wist.StSelectString(
                            id="color_by",
                            label="Compare Samples By",
                            options=[]
                        ),
                        wist.StSelectString(
                            id="filter_by",
                            label="Filter Samples",
                            options=[],
                            value=None
                        )
                    ]
                ),
                wist.StColumns(
                    id="row2",
                    children=[
                        wist.StSelectString(
                            id="tax_level",
                            label="Taxonomic Level",
                            options=tax_levels,
                            value="genus"
                        ),
                        wist.StFloat(
                            id="max_p",
                            label="Threshold p-value",
                            value=0.05
                        )
                    ]
                ),
                wist.StColumns(
                    id='row3',
                    children=[
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

    def run_self(self):

        # Get all of the ploting parameters
        kwargs = self.all_values(flatten=True)

        # Check to see if we have enough data to proceed
        msg = None

        # If no annotations were uploaded
        if self._root().abund() is None:
            msg = "Please upload abundances to proceed"

        # If no sample metadata was uploaded
        elif self._root().sample_annotations() is None:
            msg = "Please upload metadata to proceed"

        # If no comparison metric was selected
        elif kwargs["color_by"] is None or kwargs["color_by"] == "None":

            # Instruct the user to select an option
            msg = "Please select a comparison to proceed"

        if msg is not None:
            self.option("plot").main_empty.write(msg)
            return

        # Make the figure
        fig, msg = self.make_fig(
            abund_hash=self._root().abund_hash(),
            annot_hash=self._root().annot_hash(),
            **{
                kw: val
                for kw, val in kwargs.items()
                if kw != "legend"
            }
        )

        # Show the message
        if msg is not None:
            self.option("plot_msg").main_empty.write(msg)

        # Show the plot
        if fig is not None:
            self.option("plot").main_empty.plotly_chart(fig)

        # Show the legend
        if kwargs['legend'] is not None and len(kwargs['legend']) > 0:
            self.option("legend_display").main_empty.write(
                kwargs['legend']
            )

    @st.cache_data(max_entries=10)
    def make_fig(_self, **kwargs):
        """Make the primary figure for plotting."""

        # Get the abundances
        abund = _self._root().abund(
            level=kwargs["tax_level"],
            filter=kwargs["filter_by"]
        )

        # Get the annotations
        annot_df = _self._root().sample_annotations()
        color_by = kwargs["color_by"]
        try:
            meta = annot_df[color_by]
        except KeyError as e:
            return None, f"Invalid column name: {color_by} ({str(e)})"

        meta = meta.reindex(index=abund.columns).dropna()
        if meta.shape[0] < 3:
            return None, f"Not enough samples with data for: {color_by}"

        # Get the differential abundance table
        da_df, msg = _self.calc_diff_abund(
            abund.reindex(columns=meta.index),
            meta,
            continuous=is_numeric(annot_df[color_by])
        )

        fig = px.scatter(
            data_frame=da_df,
            x="Mean Abundance",
            y="p-value (-log10)",
            color="Test Statistic",
            hover_name="Organism",
            hover_data=[
                "Mean Abundance",
                "Test Statistic",
                "p-value",
                "p-value (-log10)",
                "FDR (-log10)",
                "FDR"
            ],
            color_continuous_scale="RdBu",
            log_x=True
        )
        layout = dict(
            yaxis_title="FDR-adjusted p-value (-log10)"
        )

        if kwargs["title"] is not None and kwargs["title"] != "None":
            fig.update_layout(title=kwargs["title"])
        fig.update_layout(**layout)

        return fig, msg

    @st.cache_data(max_entries=10)
    def calc_diff_abund(
        _self,
        abund: pd.DataFrame,
        meta: pd.DataFrame,
        continuous=True
    ):
        if continuous:
            df = _self.spearman(abund, meta)
            msg = "Test: Spearman Rank-Order Correlation Coefficient"
        else:
            df = _self.anova(abund, meta)
            msg = "Test: ANOVA (one-way)"

        df = df.assign(
            FDR=multipletests(df["p-value"])[1],
            **{
                "p-value (-log10)": lambda d: -np.log10(d['p-value'].clip(lower=d['p-value'][d['p-value'] > 0].min())), # noqa
                "FDR (-log10)": lambda d: -np.log10(d['FDR'].clip(lower=d['FDR'][d['FDR'] > 0].min())) # noqa
            }
        )

        return df, msg

    def spearman(
        _self,
        abund: pd.DataFrame,
        meta: pd.DataFrame,
    ) -> pd.DataFrame:

        return pd.DataFrame([
            dict(
                Organism=org,
                **_self.spearman_single(org_abund, meta)
            )
            for org, org_abund in abund.iterrows()
        ])

    def spearman_single(self, org_abund, meta) -> dict:
        r = spearmanr(org_abund.values, meta.values)

        return {
            "Test Statistic": r.statistic,
            "p-value": r.pvalue,
            "Mean Abundance": org_abund.mean()
        }

    def anova(
        _self,
        abund: pd.DataFrame,
        meta: pd.DataFrame,
    ) -> pd.DataFrame:

        return pd.DataFrame([
            dict(
                Organism=org,
                **_self.anova_single(org_abund, meta)
            )
            for org, org_abund in abund.iterrows()
        ])

    def anova_single(self, org_abund, meta) -> dict:
        r = f_oneway(*[
            group_abund.tolist()
            for _, group_abund in org_abund.groupby(meta)
        ])

        return {
            "Test Statistic": r.statistic,
            "p-value": r.pvalue,
            "Mean Abundance": org_abund.mean()
        }
