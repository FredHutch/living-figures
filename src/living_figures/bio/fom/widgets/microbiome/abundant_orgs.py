from living_figures.bio.fom.widgets.microbiome.base_plots import MicrobiomePlot
from living_figures.helpers.constants import tax_levels
from living_figures.helpers.parse_numeric import is_numeric
from living_figures.helpers.scaling import convert_text_to_scalar
from living_figures.helpers.sorting import sort_table
import widgets.streamlit as wist
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st


class AbundantOrgs(MicrobiomePlot):

    label = "Abundant Organisms"

    children = [
        wist.StExpander(
            id="options",
            children=[
                wist.StColumns(
                    id="row1",
                    children=[
                        wist.StSelectString(
                            id='plot_type',
                            label="Plot Type",
                            options=['Stacked Bars', 'Heatmap'],
                            value='Stacked Bars'
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
                        wist.StSelectString(
                            id="heatmap_cpal",
                            label="Heatmap Color Palette",
                            options=px.colors.named_colorscales(),
                            value="blues"
                        ),
                        wist.StSelectString(
                            id="annot_cpal",
                            label="Annotation Color Palette",
                            options=px.colors.named_colorscales(),
                            value="bluered"
                        )
                    ]
                ),
                wist.StColumns(
                    id="row5",
                    children=[
                        wist.StFloat(
                            id="annot_size",
                            label="Annotation Size",
                            value=0.05,
                            min=0.
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
                    id="row6",
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

    @st.cache_data(max_entries=10)
    def get_abundance_data(
        _self,
        tax_level: str,
        filter_by: str,
        n_orgs: int,
        abund_hash
    ):

        # Get the abundances, filtering to the specified taxonomic level
        # Columns are samples, rows are organisms
        abund: pd.DataFrame = _self._root().abund(
            level=tax_level,
            filter=filter_by
        )

        if abund is None:
            return

        # If there are no more organisms than the specified max
        if abund.shape[0] <= n_orgs:
            return abund

        # Otherwise, we need to filter down the number of organisms being shown

        # Compute the average abundance of each organism
        mean_abund = abund.mean(axis=1).sort_values(ascending=False)

        to_keep = mean_abund.index.values[:(n_orgs-1)]

        abund = pd.concat([
            abund.reindex(index=to_keep),
            pd.DataFrame(dict(
                Other=abund.drop(index=to_keep).sum()
            )).T
        ])

        return abund

    @st.cache_data(max_entries=10)
    def get_plotting_data(
        _self,
        tax_level,
        filter_by,
        n_orgs,
        color_by,
        sort_by,
        abund_hash,
        annot_hash
    ):
        """Return the data used for plotting."""

        # Get the abundance data to plot
        abund_df = _self.get_abundance_data(
            tax_level,
            filter_by,
            n_orgs,
            abund_hash
        )

        # If there is no abundance data
        if abund_df is None:
            return None, None

        # Get the metadata (if any was provided)
        sample_annots: pd.DataFrame = _self._root().sample_annotations()

        # If there is metadata and the user wants to display it
        if len(color_by) > 0 and sample_annots is not None:

            annot_df = sample_annots.reindex(
                columns=color_by,
                index=abund_df.columns.values
            ).dropna()

            # If there are no samples with the selected metadata
            if annot_df.shape[0] == 0:
                return None, None

            # Only keep the abundances which have annotations
            abund_df = abund_df.reindex(
                columns=annot_df.index.values
            )

        else:
            annot_df = None

        # If the user requested to sort samples by organism abundances
        if sort_by == "Organism Abundances":

            # Sort the abundance table
            abund_df = sort_table(abund_df)

        # If the user requested to sort samples by annotations
        elif sort_by == "Selected Metadata" and annot_df is not None:

            # Sort the annotation table
            annot_df = annot_df.sort_values(
                by=list(annot_df.columns.values)
            )

            # Order the abundances to match
            abund_df = abund_df.reindex(columns=annot_df.index.values)

        # Order the annotations to match the abundances
        if annot_df is not None:
            annot_df = annot_df.reindex(index=abund_df.columns.values)

        return abund_df, annot_df

    @st.cache_data(max_entries=10)
    def make_fig(
        _self,
        tax_level,
        filter_by,
        n_orgs,
        color_by,
        sort_by,
        annot_size,
        plot_type,
        title,
        abund_hash,
        annot_hash
    ):
        """Make the figure to plot"""

        # Get the plotting data
        abund_df, annot_df = _self.get_plotting_data(
            tax_level,
            filter_by,
            n_orgs,
            color_by,
            sort_by,
            abund_hash,
            annot_hash
        )

        # If there is no data
        if abund_df is None:
            # Don't make a plot
            return

        # Set up the size of the annotations
        annot_frac = min(
            0.5,
            0.02 + (annot_size * float(len(color_by)))
        )
        row_heights = [1 - annot_frac, annot_frac]

        # Set up the plot area
        fig = make_subplots(
            rows=1 if annot_df is None else 2,
            cols=1,
            vertical_spacing=0.01,
            horizontal_spacing=0.01,
            start_cell="top-left",
            row_heights=None if annot_df is None else row_heights,
            shared_xaxes=True
        )

        # Plot the heatmap / stacked bars
        fig.add_traces(_self.plot_abund(abund_df), rows=1, cols=1)

        if plot_type == "Stacked Bars":
            fig.update_layout(
                barmode='stack',
                yaxis_title="Relative Abundance (%)"
            )

        # Plot the annotations
        if len(color_by) > 0 and annot_df is not None:
            fig.add_trace(_self.plot_annot(annot_df), row=2, col=1)

        # If there is a title
        if title is not None and title != "None":
            fig.update_layout(title=title)

        return fig

    def run_self(self):

        # Get the plotting options
        params = self.all_values(flatten=True)

        # Get the figure to plot
        fig = self.make_fig(
            params['tax_level'],
            params['filter_by'],
            params['n_orgs'],
            params['color_by'],
            params['sort_by'],
            params['annot_size'],
            params['plot_type'],
            params['title'],
            self._root().abund_hash(),
            self._root().annot_hash()
        )

        # If there is a figure
        if fig is not None:

            # Display it in the 'plot' child resource
            plot_area = self._get_child("plot")
            plot_area.main_empty.plotly_chart(
                fig,
                use_container_width=True
            )

        # If there is a legend
        if params['legend'] is not None:
            self._get_child(
                "legend_display"
            ).main_empty.markdown(
                params['legend']
            )

    def plot_abund(self, abund_df):

        if self.val("plot_type") == "Heatmap":
            return self.plot_heatmap(abund_df)
        else:
            return self.plot_bars(abund_df)

    def plot_heatmap(self, abund_df: pd.DataFrame):

        # Color scale used for the heatmap
        colorscale = self.val("heatmap_cpal")

        # Mouseover text
        text_df = abund_df.apply(
            lambda c: [
                f"Sample: {c.name}<br>Organism: {n}<br>Abundance: {a:.4g}%"
                for n, a in c.items()
            ]
        )

        return [
            go.Heatmap(
                x=abund_df.columns.values,
                y=abund_df.index.values,
                z=abund_df.values,
                colorscale=colorscale,
                text=text_df.values,
                hoverinfo="text",
                colorbar_title="Relative<br>Abundance<br>(%)"
            )
        ]

    def plot_bars(self, abund_df):

        return [
            go.Bar(
                name=org_name,
                x=org_abund.index.values,
                y=org_abund.values,
                hovertext=[
                    f"{sample}<br>{org_name}: {abund:.4g}%"
                    for sample, abund in org_abund.items()
                ]
            )
            for org_name, org_abund in abund_df.iterrows()
        ]

    def plot_annot(self, annot_df):

        # Capture the annotations as text
        text_df = annot_df.applymap(
            lambda i: "" if i is None else str(i)
        ).apply(
            lambda c: c.apply(
                lambda i: f"{c.name}: {i}"
            )
        )

        # For any text columns, scale to a number
        for cname in annot_df:
            if not is_numeric(annot_df[cname]):
                annot_df = annot_df.assign(**{
                    cname: convert_text_to_scalar(annot_df[cname])
                })

        return go.Heatmap(
            x=annot_df.index.values,
            y=annot_df.columns.values,
            z=annot_df.T.values,
            colorscale=self.option("annot_cpal").get_value(),
            text=text_df.T.values,
            hoverinfo="text",
            showscale=False,
        )
