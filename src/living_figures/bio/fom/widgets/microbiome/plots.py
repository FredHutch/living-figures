import widgets.streamlit as wist
from widgets.base.exceptions import WidgetFunctionException
import pandas as pd
import plotly.express as px
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import streamlit as st
from living_figures.helpers.constants import tax_levels


class Ordination(wist.StResource):
    label="Ordination (PCA/t-SNE)"
    children = [
        wist.StColumns(
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
    ]

    def run_ordination(self):
        """Perform ordination on the abundance data."""

        # Set up the cache
        if st.session_state.get("ordination_cache") is None:
            st.session_state["ordination_cache"] = dict()

        # Get the hash of the input data
        abund_hash = self._root().abund_hash()

        # Taxonomic level to use
        level = self.get(["columns", "tax_level"])

        # Type of ordination
        ord_type = self.get(["columns", "ord_type"])

        # Set the cache key based on the input data and analysis details
        cache_key = f"{abund_hash}:{level}:{ord_type}"

        # Get the abundances, filtering to the specified taxonomic level
        # Columns are samples, rows are organisms
        abund = self._root().abund(level=level)

        # If there are no abundances
        if abund is None:

            # Stop
            msg = "No abundances available for ordination"
            self.main_container.write(msg)
            return

        # Remove any samples which sum to 0
        abund = abund.reindex(
            columns=abund.columns.values[
                abund.sum() > 0
            ]
        )

        self.main_container.write(
            f"Running {ord_type} on {abund.shape[1]:,} samples using {abund.shape[0]:,} {level}-level organisms"
        )

        # Normalize all abundances to proportions
        abund = abund / abund.sum()

        # Only compute if the cache is empty
        if st.session_state["ordination_cache"].get(cache_key) is None:

            if ord_type == 'PCA':
                st.session_state["ordination_cache"][cache_key] = self.run_pca(abund)
            elif ord_type == 't-SNE':
                st.session_state["ordination_cache"][cache_key] = self.run_tsne(abund)
            else:
                msg = "Ordination type not recognized"
                raise WidgetFunctionException(msg)

        return st.session_state["ordination_cache"][cache_key]

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

        tsne = TSNE()
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

        # Make a plot
        fig = px.scatter(
            data_frame=plot_df,
            x=plot_df.columns.values[0],
            y=plot_df.columns.values[1]
        )

        self.main_container.plotly_chart(fig)
