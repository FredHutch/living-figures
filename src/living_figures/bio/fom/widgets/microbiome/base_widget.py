import streamlit as st
from typing import List, Union
import numpy as np
import pandas as pd
import widgets.streamlit as wist
from widgets.base.exceptions import WidgetFunctionException
from living_figures.helpers import parse_numeric
from living_figures.helpers import is_numeric


class BaseMicrobiomeExplorer(wist.StreamlitWidget):

    def msg(self, msg):
        """Write to the message container."""
        self.main_container.write(msg)

    def abund(self, level=None, filter='None') -> pd.DataFrame:
        """
        Return the abundance table
        """

        # Get the abundances
        abund: pd.DataFrame = self.get(["data", "abund"])

        # Get the sample annotations
        sample_annots = self.sample_annotations()

        return self._make_abund(abund, sample_annots, level, filter)

    @st.cache_data
    def _make_abund(
        _self,
        abund: pd.DataFrame,
        sample_annots: pd.DataFrame,
        level: str,
        filter: str
    ) -> pd.DataFrame:

        if abund.shape[0] == 0:
            return

        # If the level is not specified
        if level is None:
            # Return everything
            pass

        # If a level is specified
        else:

            # Get the taxonomic information for each row
            index_orgs = _self.get(["data", "abund"], attr="index_orgs")

            # Filter down to the rows which are assigned at that level
            abund = abund.reindex(
                index=index_orgs.query(
                    f"level == '{level}'"
                ).index
            )

            if abund.shape[0] == 0:
                msg = f"No organisms classified at the {level} level"
                raise WidgetFunctionException(msg)

            # Rename the table for just the organism name
            abund = abund.rename(
                index=index_orgs['name'].get
            )

        # If a filter was specified
        if filter is not None and filter != 'None':

            # Apply the filter
            query_col, query_val = filter.split(" == ", 1)
            sample_annots = sample_annots.loc[
                sample_annots[query_col].apply(str) == query_val
            ]
            filtered_samples = set(list(sample_annots.index.values))

            # Subset the abundances to that set of samples
            abund = abund.reindex(
                columns=[
                    cname for cname in abund.columns.values
                    if cname in filtered_samples
                ]
            )

        # Remove any samples which sum to 0
        abund = abund.reindex(
            columns=abund.columns.values[
                abund.sum() > 0
            ]
        )

        if abund.shape[1] == 0:
            return

        # Normalize all abundances to percentages
        abund = 100 * abund / abund.sum()

        return abund

    def abund_hash(self) -> pd.DataFrame:
        """
        Return the hash of the abundance table
        """

        return self.get(["data", "abund"], attr="hash")

    def annot_hash(self) -> pd.DataFrame:
        """
        Return the hash of the annotation table
        """

        return self.get(["data", "annots"], attr="hash")

    def sample_annotations(self) -> Union[None, pd.DataFrame]:
        """Return the table of sample annotations."""

        # Get the value of the sample annotation resource
        annots: pd.DataFrame = self.get(["data", "annots"])

        # If the sample annotations have not been provided
        if annots.shape[0] == 0:
            return None

        # Get the set of sample IDs from the abundance table
        abund_samples = self.get(['data', 'abund']).columns.values

        # If the abundances have not been provided
        if len(abund_samples) == 0:
            return None

        # If both have been provided, return the annotations
        # specifically for the set of samples in the abundance table
        annots = annots.reindex(index=abund_samples)

        # Drop any values which are noted by text as missing
        annots = annots.replace(
            to_replace=['N/A', 'NA', 'missing', 'NaN'],
            value=np.nan
        )

        # Drop any columns for which no values are present
        cols_to_drop = [
            cname
            for cname, cvals in annots.items()
            if cvals.dropna().shape[0] == 0
        ]
        if len(cols_to_drop) > 0:
            annots = annots.drop(columns=cols_to_drop)

        # If there are no columns remaining
        if annots.shape[1] == 0:
            return None

        # Try to convert any values to numeric, if possible
        annots = parse_numeric(annots)

        # Return the data which passes this filtering regime
        return annots

    def sample_filters(self, max_categories=10) -> List[str]:
        """Return the list of possible filters based on sample metadata."""

        # Get all of the sample annotations provided by the user
        annots = self.sample_annotations()

        # Build a list of possible filters
        filters = ['None']

        if annots is None or annots.shape[1] == 0:
            return filters

        # For each category of metadata
        for cname, cvals in annots.items():

            # Get the unique values
            unique_vals = cvals.dropna().unique()

            # Skip if there are > max_categories values
            if unique_vals.shape[0] > max_categories:
                continue

            # Add each value to the list of filters
            for uval in unique_vals:

                # Wrap strings in quotes
                if isinstance(uval, str):
                    filter_val = f"'{uval}'"
                else:
                    filter_val = str(uval)

                filters.append(
                    f"{cname} == {filter_val}"
                )

        return filters

    def sample_colors(self, max_categories=10, include_none=True) -> List[str]:
        """Return the list of plot colorings based on sample metadata."""

        # Get all of the sample annotations provided by the user
        annots = self.sample_annotations()

        # Build a list of possible colors
        colors = ['None'] if include_none else []

        if annots is None or annots.shape[1] == 0:
            return colors

        # For each category of metadata
        for cname, cvals in annots.items():

            # If the column is numeric
            if is_numeric(cvals):

                # Add it to the list
                colors.append(cname)

            # If it is categorical
            else:

                # Get the unique values
                unique_vals = cvals.dropna().unique()

                # If there are no more than max_categories values
                if unique_vals.shape[0] <= max_categories:

                    # Add it to the list
                    colors.append(cname)

        return colors

    def update_options(self) -> None:
        """Update the menu selection items based on the user inputs."""

        # Update the Ordination and Abundant Organism plots
        for plot_type in [
            "ordination",
            "abundant_orgs",
            "alpha_diversity",
            "beta_diversity",
            "differential_abundance",
        ]:

            # For each of the elements of this type
            for plot_elem in self._find_child(plot_type):

                # Update the 'color_by' and 'filter_by' menu options

                # Update the sample colors
                plot_elem.update_options(
                    self.sample_colors(
                        # Only include a "None" value for ordination
                        include_none=plot_type != "abundant_orgs"
                    ),
                    "color_by"
                )
                # Update the filter_by for all plot types
                plot_elem.update_options(self.sample_filters(), "filter_by")
