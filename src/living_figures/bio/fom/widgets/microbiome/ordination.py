from typing import Union
import widgets.streamlit as wist
from widgets.base.exceptions import WidgetFunctionException
from living_figures.bio.fom.widgets.microbiome.base_plots import MicrobiomePlot
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import streamlit as st
from living_figures.helpers.constants import tax_levels


class Ordination(MicrobiomePlot):

    label = "Ordination (PCA/t-SNE)"

    children = [
        wist.StExpander(
            id="options",
            children=[
                wist.StColumns(
                    id="row1",
                    children=[
                        wist.StSelectString(
                            id='ord_type',
                            label="Ordination Type",
                            options=['PCA', 't-SNE'],
                            value='PCA'
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
                            label="Color Samples By",
                            options=[],
                            value=None
                        )
                    ]
                ),
                wist.StColumns(
                    id="row3",
                    children=[
                        wist.StCheckbox(
                            id='pca_loadings',
                            label="Show PCA Loadings",
                            value=False
                        ),
                        wist.StCheckbox(
                            id='3D',
                            label="3D Plot",
                            value=False
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
        wist.StResource(id="ord_msg"),
        wist.StResource(id="legend_display")
    ]

    @st.cache_data(max_entries=10)
    def run_ordination(
        _self,
        tax_level,
        filter_by,
        ord_type,
        abund: pd.DataFrame
    ) -> Union[None, pd.DataFrame]:
        """Perform ordination on the abundance data."""

        # If there are no abundances
        if abund is None:

            # Stop
            msg = "No abundances available for ordination"
            return None, None, msg

        msg = f"Running {ord_type} on {abund.shape[1]:,} samples"
        msg = f"{msg} using {abund.shape[0]:,}"
        msg = f"{msg} {tax_level}-level organisms"
        if filter_by is not None and filter_by != 'None':
            msg = msg + "  \n" + f"Filtering to {filter_by}"

        if ord_type == 'PCA':
            proj, loadings = _self.run_pca(abund)
        elif ord_type == 't-SNE':
            proj, loadings = _self.run_tsne(abund)
        else:
            msg = "Ordination type not recognized"
            raise WidgetFunctionException(msg)

        return proj, loadings, ""

    def run_pca(self, abund: pd.DataFrame):
        """Ordinate data using PCA"""

        pca = PCA()
        ord_mat = pca.fit_transform(abund.T)

        # Name each PC for the amount of variance it explains
        pc_names = [
            f"PC{i+1} ({round(v * 100, 1)}%)"
            for i, v in enumerate(pca.explained_variance_ratio_)
        ]

        # Projection of the samples in the ordination space
        coords = pd.DataFrame(
            ord_mat,
            columns=pc_names,
            index=abund.columns
        )

        # Center to the mean
        coords = coords - coords.mean()

        # Loadings of each variable for each axis
        loadings = pd.DataFrame(
            pca.components_,
            index=pc_names,
            columns=abund.index.values
        )

        return coords, loadings

    def run_tsne(self, abund: pd.DataFrame):
        """Ordinate data using t-SNE"""

        tsne = TSNE(
            n_components=3 if self.val("3D") else 2
        )
        ord_mat = tsne.fit_transform(abund.T)
        coords = pd.DataFrame(
            ord_mat,
            columns=[
                f"t-SNE {i+1}"
                for i in range(ord_mat.shape[1])
            ],
            index=[
                org.split(";")[-1]
                for org in abund.columns
            ]
        )

        return coords, None

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

        fig, msg = self.build_fig(
            params["tax_level"],
            params["filter_by"],
            params["ord_type"],
            abund,
            sample_annots,
            params["3D"],
            params["color_by"],
            params["title"],
            params["pca_loadings"],
        )

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
        tax_level,
        filter_by,
        ord_type,
        abund,
        sample_annots,
        is_3d,
        color_by,
        title,
        pca_loadings
    ):

        # Get the ordinated data
        plot_df, loadings, msg = _self.run_ordination(
            tax_level,
            filter_by,
            ord_type,
            abund
        )

        if plot_df is None:
            return None, msg

        # Add the metadata (if any was provided)
        if sample_annots is not None:
            plot_df = plot_df.merge(
                sample_annots,
                left_index=True,
                right_index=True
            )

        # Get the coloring column
        if color_by == 'None':
            color_by = None

        # Set up the data which will be used to build the plot
        plot_kwargs = dict(
            data_frame=plot_df.reset_index(
            ).rename(
                columns=dict(index="sample")
            ),
            x=plot_df.columns.values[0],
            y=plot_df.columns.values[1],
            hover_data=[
                plot_df.columns.values[0],
                plot_df.columns.values[1],
                "sample"
            ],
            color=color_by
        )
        if color_by is not None:
            plot_kwargs["hover_data"].append(color_by)

        # If the 3D plot was requested
        if is_3d:
            plot_f = px.scatter_3d
            plot_kwargs['z'] = plot_df.columns.values[2]
        else:
            plot_f = px.scatter

        # Make a plot
        fig = plot_f(**plot_kwargs)

        # Add the PCA loadings, if requested
        if pca_loadings:
            _self.add_pca_loadings(
                fig,
                plot_df,
                loadings,
                is_3d
            )

        # If there is a title
        if title is not None and title != "None":
            fig.update_layout(title=title)

        return fig, msg

    def add_pca_loadings(
        self,
        fig,
        plot_df,
        loadings,
        is_3d
    ):

        # If no value has been computed
        if loadings is None:
            return

        # Number of dimensions
        ndims = 2 + is_3d

        # Just pick the number of axes used in the plot
        loadings = loadings.head(ndims)

        # Score the organisms based on the absolute sum of loadings
        org_score = loadings.abs().sum()

        # Pick the number of organisms to plot
        cutoff_score = org_score.sort_values(
            ascending=False
        ).values[
            ndims
        ] / 2.

        loadings = loadings.reindex(
            columns=org_score.index.values[
                org_score >= cutoff_score
            ]
        )

        # Scale each loading to fit nicely on the plot
        loadings = (
            plot_df.reindex(
                columns=loadings.index.values
            ).abs().max() * loadings.T / loadings.T.abs().max()
        ).T

        for org_name, org_coords in loadings.items():

            line_props = dict(
                x=[0, org_coords.values[0]],
                y=[0, org_coords.values[1]],
                mode='lines',
                name=org_name
            )
            if self.val("3D"):
                line_props['z'] = [0, org_coords.values[2]]
                trace_f = go.Scatter3d
            else:
                trace_f = go.Scatter

            fig.add_trace(
                trace_f(**line_props)
            )
