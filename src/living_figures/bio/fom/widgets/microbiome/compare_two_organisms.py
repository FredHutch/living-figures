import streamlit as st
from living_figures.bio.fom.widgets.microbiome.base_plots import MicrobiomePlot
import widgets.streamlit as wist
import pandas as pd
import plotly.express as px


class CompareTwoOrganisms(MicrobiomePlot):
    """
    Compare the relative abundance of two organisms across samples.
    """

    label = "Compare Two Organisms"

    children = [
        wist.StExpander(
            id="options",
            children=[
                wist.StColumns(
                    id="row1",
                    children=[
                        wist.StSelectString(
                            id='org1',
                            label="Organism 1",
                            options=[]
                        ),
                        wist.StSelectString(
                            id='org2',
                            label="Organism 2",
                            options=[]
                        )
                    ]
                ),
                wist.StColumns(
                    id="row2",
                    children=[
                        wist.StSelectString(
                            id="color_by",
                            label="Color Samples By",
                            options=[]
                        ),
                        wist.StSelectString(
                            id="filter_by",
                            label="Filter Samples By",
                            options=[],
                            value=None
                        )
                    ]
                ),
                wist.StColumns(
                    id="row3",
                    children=[
                        wist.StCheckbox(
                            id="log",
                            label="Log10 Scale",
                            value=False
                        ),
                        wist.StInteger(
                            label="Figure Height",
                            id="height",
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

    @st.cache_data(max_entries=10)
    def get_abundance_data(
        _self,
        tax_level: str,
        filter_by: str,
        abund_hash,
        annot_hash
    ):

        # Get the abundances, filtering to the specified taxonomic level
        # Columns are samples, rows are organisms
        return _self._root().abund(
            level=tax_level,
            filter=filter_by
        )

    @st.cache_data(max_entries=10)
    def make_fig(
        _self,
        org1,
        org2,
        color_by,
        filter_by,
        log,
        height,
        title,
        abund_hash,
        annot_hash
    ):

        # Get the plotting data
        plot_df = _self.get_plotting_data(
            org1,
            org2,
            color_by,
            filter_by,
            abund_hash,
            annot_hash
        )

        if plot_df is None:
            return

        # If the log-transform was specified
        if log:

            for kw in ['_ABUND_1', '_ABUND_2']:

                # If all values are 0, take no action
                if plot_df[kw].max() == 0:
                    return

                # Find the lowest non-zero value
                lower_bound = plot_df.loc[plot_df[kw] > 0, kw].min()

                # Set the floor so that the log renders appropriately
                plot_df = plot_df.assign(
                    _ABUND=plot_df[kw].clip(
                        lower=lower_bound
                    )
                )

        fig = px.scatter(
            plot_df.reset_index(),
            x="_ABUND_1",
            y="_ABUND_2",
            log_x=log,
            log_y=log,
            height=height,
            labels=dict(
                _ABUND_1=org1.replace("_", " "),
                _ABUND_2=org2.replace("_", " ")
            ),
            color=color_by if color_by != 'None' else None,
            hover_name="index"
        )

        # If there is a title
        if title is not None and title != "None":
            fig.update_layout(title=title)

        return fig

    def get_org_abund(
        _self,
        org: str,
        filter_by,
        abund_hash,
        annot_hash
    ):

        # The `org` contains the rank and the name
        rank, name = org.split(": ", 1)

        # Get the abundance data for that rank
        rank_abund: pd.DataFrame = _self.get_abundance_data(
            rank,
            filter_by,
            abund_hash,
            annot_hash
        )
        if rank_abund is None:
            return

        return rank_abund.loc[name]

    @st.cache_data(max_entries=10)
    def get_plotting_data(
        _self,
        org1,
        org2,
        color_by,
        filter_by,
        abund_hash,
        annot_hash
    ):

        # Get the abundances
        org1_abund = _self.get_org_abund(
            org1,
            filter_by,
            abund_hash,
            annot_hash
        )
        if org1_abund is None:
            return
        org2_abund = _self.get_org_abund(
            org2,
            filter_by,
            abund_hash,
            annot_hash
        )
        if org2_abund is None:
            return

        # Get the metadata (if any was provided)
        sample_annots: pd.DataFrame = _self._root().sample_annotations()
        if sample_annots is None:
            return pd.DataFrame(dict(
                _ABUND_1=org1_abund,
                _ABUND_2=org2_abund
            ))

        # Add the organism abundance as a column to the sample annotations
        return sample_annots.reindex(
            index=org1_abund.index
        ).assign(
            _ABUND_1=org1_abund,
            _ABUND_2=org2_abund
        )

    def run_self(self):

        # Get all of the ploting parameters
        params = self.all_values(flatten=True)

        # If no organism is selected, take no action
        for kw in ['org1', 'org2']:
            if params[kw] is None or params[kw] == 'None':
                return

        # Get the figure to plot
        fig = self.make_fig(
            params['org1'],
            params['org2'],
            params['color_by'],
            params['filter_by'],
            params['log'],
            params['height'],
            params['title'],
            self._root().abund_hash(),
            self._root().annot_hash(),
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
