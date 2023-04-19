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

    def make_cache_key(self, val_str: str):
        """Return a cache for the ordination object(s)."""

        # Get the hash of the input data
        abund_hash = self._root().abund_hash()

        # Get the plotting options
        params = self.all_values(flatten=True)

        # Set the cache key based on the input data and analysis details
        cache_key = f"{abund_hash}:{params['tax_level']}:{params['ord_type']}:{2 + params['3D']}D:{params['filter_by']}:{val_str}" # noqa

        return cache_key

    def run_ordination(self) -> Union[None, pd.DataFrame]:
        """Perform ordination on the abundance data."""

        # Set up the cache
        if st.session_state.get("ordination_cache") is None:
            st.session_state["ordination_cache"] = dict()

        # Get the plotting options
        params = self.all_values(flatten=True)

        # Get the cache key
        cache_key = self.make_cache_key("projection")

        # Get the abundances, filtering to the specified taxonomic level
        # Columns are samples, rows are organisms
        abund: pd.DataFrame = self._root().abund(
            level=params['tax_level'],
            filter=params['filter_by']
        )

        # If there are no abundances
        if abund is None:

            # Stop
            msg = "No abundances available for ordination"
            self._get_child("ord_msg").main_empty.write(msg)
            return

        msg = f"Running {params['ord_type']} on {abund.shape[1]:,} samples"
        msg = f"{msg} using {abund.shape[0]:,}"
        msg = f"{msg} {params['tax_level']}-level organisms"
        if params['filter_by'] is not None and params['filter_by'] != 'None':
            msg = msg + "  \n" + f"Filtering to {params['filter_by']}"
        self._get_child("ord_msg").main_empty.write(msg)

        # Only compute if the cache is empty
        if self.get_cache(cache_key) is None:

            if params['ord_type'] == 'PCA':
                proj, loadings = self.run_pca(abund)
            elif params['ord_type'] == 't-SNE':
                proj, loadings = self.run_tsne(abund)
            else:
                msg = "Ordination type not recognized"
                raise WidgetFunctionException(msg)

            self.set_cache(cache_key, proj)
            self.set_cache(self.make_cache_key("loadings"), loadings)

        return self.get_cache(cache_key)

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
            n_components=3 if self.option("3D").get_value() else 2
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

        # Get the ordinated data
        plot_df = self.run_ordination()
        if plot_df is None:
            return

        # Add the metadata (if any was provided)
        sample_annots = self._root().sample_annotations()
        if sample_annots is not None:
            plot_df = plot_df.merge(
                sample_annots,
                left_index=True,
                right_index=True
            )

        # Get the coloring column
        color_by = self.option("color_by").get_value()
        if color_by == 'None':
            color_by = None

        # Set up the data which will be used to build the plot
        plot_kwargs = dict(
            data_frame=plot_df,
            x=plot_df.columns.values[0],
            y=plot_df.columns.values[1],
            color=color_by
        )

        # If the 3D plot was requested
        if self.option("3D").get_value():
            plot_f = px.scatter_3d
            plot_kwargs['z'] = plot_df.columns.values[2]
        else:
            plot_f = px.scatter

        # Make a plot
        fig = plot_f(**plot_kwargs)

        # Add the PCA loadings, if requested
        self.add_pca_loadings(fig)

        # If there is a title
        title = self.option("title").get_value()
        if title is not None and title != "None":
            fig.update_layout(title=title)

        # Add the plot to the display
        self._get_child("plot").main_empty.plotly_chart(fig)

        # If there is a legend
        legend = self.option("legend").get_value()
        if legend is not None:
            self._get_child(
                "legend_display"
            ).main_empty.markdown(legend)

    def add_pca_loadings(self, fig):

        if not self.option("pca_loadings").get_value():
            return

        # Get the key used in the cache for the loadings
        loadings = self.get_cache(
            self.make_cache_key("loadings")
        )

        if loadings is None:
            return

        # Number of dimensions
        ndims = 2 + self.option("3D").get_value()

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

        for org_name, org_coords in loadings.items():

            line_props = dict(
                x=[0, org_coords.values[0]],
                y=[0, org_coords.values[1]],
                mode='lines',
                name=org_name
            )
            if self.option("3D").get_value():
                line_props['z'] = [0, org_coords.values[2]]
                trace_f = go.Scatter3d
            else:
                trace_f = go.Scatter

            fig.add_trace(
                trace_f(**line_props)
            )
