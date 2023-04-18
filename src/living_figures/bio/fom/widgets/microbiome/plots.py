from typing import Union
import widgets.streamlit as wist
from widgets.base.exceptions import WidgetFunctionException
import pandas as pd
import plotly.express as px
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import streamlit as st
from living_figures.helpers.constants import tax_levels


class Ordination(wist.StResource):

    label = "Ordination (PCA/t-SNE)"

    children = [
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
            id="row2",
            children=[
                wist.StCheckbox(
                    id='3D',
                    label="3D Plot",
                    value=False
                ),
                wist.StResource(
                    id="blank1"
                ),
                wist.StResource(
                    id="blank2"
                )
            ]
        ),
        wist.StResource(id="plot"),
        wist.StResource(id="ord_msg")
    ]

    def update_options(self, options):
        """Update the set of options for user-provided metadata."""

        # If this element is disabled
        if self.main_container is None:
            return

        # Color Samples By
        color_by = self._get_child("row1", "color_by")
        if color_by.get_attr("options") != options:
            color_by.set(attr="options", value=options)

        # Regenerate the plot
        self.run_self()

    def run_ordination(self) -> Union[None, pd.DataFrame]:
        """Perform ordination on the abundance data."""

        # Set up the cache
        if st.session_state.get("ordination_cache") is None:
            st.session_state["ordination_cache"] = dict()

        # Get the hash of the input data
        abund_hash = self._root().abund_hash()

        # Taxonomic level to use
        level = self.get(["row1", "tax_level"])

        # Type of ordination
        ord_type = self.get(["row1", "ord_type"])

        # Set the cache key based on the input data and analysis details
        is_3d = self.get(["row2", "3D"])
        cache_key = f"{abund_hash}:{level}:{ord_type}:{2 + is_3d}D"

        # Get the abundances, filtering to the specified taxonomic level
        # Columns are samples, rows are organisms
        abund = self._root().abund(level=level)

        # If there are no abundances
        if abund is None:

            # Stop
            msg = "No abundances available for ordination"
            self._get_child("ord_msg").main_empty.write(msg)
            return

        # Remove any samples which sum to 0
        abund = abund.reindex(
            columns=abund.columns.values[
                abund.sum() > 0
            ]
        )

        msg = f"Running {ord_type} on {abund.shape[1]:,} samples"
        msg = f"{msg} using {abund.shape[0]:,} {level}-level organisms"
        self._get_child("ord_msg").main_empty.write(msg)

        # Normalize all abundances to proportions
        abund = abund / abund.sum()

        # Only compute if the cache is empty
        if self.get_cache(cache_key) is None:

            if ord_type == 'PCA':
                self.set_cache(cache_key, self.run_pca(abund))
            elif ord_type == 't-SNE':
                self.set_cache(cache_key, self.run_tsne(abund))
            else:
                msg = "Ordination type not recognized"
                raise WidgetFunctionException(msg)

        return self.get_cache(cache_key)

    def set_cache(self, cache_key, value) -> None:
        st.session_state["ordination_cache"][cache_key] = value

    def get_cache(self, cache_key):
        return st.session_state["ordination_cache"].get(cache_key)

    def run_pca(self, abund: pd.DataFrame):
        """Ordinate data using PCA"""

        pca = PCA()
        ord_mat = pca.fit_transform(abund.T)
        return pd.DataFrame(
            ord_mat,
            columns=[
                f"PC{i+1} ({round(v * 100, 1)}%)"
                for i, v in enumerate(pca.explained_variance_ratio_)
            ],
            index=abund.columns
        )

    def run_tsne(self, abund: pd.DataFrame):
        """Ordinate data using t-SNE"""

        tsne = TSNE(
            n_components=3 if self.get(["row2", "3D"]) else 2
        )
        ord_mat = tsne.fit_transform(abund.T)
        return pd.DataFrame(
            ord_mat,
            columns=[
                f"t-SNE {i+1}"
                for i in range(ord_mat.shape[1])
            ],
            index=abund.columns
        )

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

        # Set up the data which will be used to build the plot
        plot_kwargs = dict(
            data_frame=plot_df,
            x=plot_df.columns.values[0],
            y=plot_df.columns.values[1],
            color=self.get(["row1", "color_by"])
        )

        # If the 3D plot was requested
        if self.get(["row2", "3D"]):
            plot_f = px.scatter_3d
            plot_kwargs['z'] = plot_df.columns.values[2]
        else:
            plot_f = px.scatter

        # Make a plot
        fig = plot_f(**plot_kwargs)

        # Add the plot to the display
        self._get_child("plot").main_empty.plotly_chart(fig)
