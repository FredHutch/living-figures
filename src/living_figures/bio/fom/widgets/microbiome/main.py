from copy import deepcopy
import numpy as np
import pandas as pd
from living_figures.bio.fom.widgets.microbiome import MicrobiomeAbund
from living_figures.bio.fom.widgets.microbiome import Ordination
from living_figures.helpers import parse_numeric
from typing import Union
import widgets.streamlit as wist
from widgets.base.exceptions import WidgetFunctionException


class MicrobiomeExplorer(wist.StreamlitWidget):
    """
    Widget used for the analysis of microbiome data.

    Input data:
        - Microbiome abundance data, from a variety of file formats
        - Sample annotation metadata
        - Microbe anotation metadata

    Types of analysis:
        - Ordination of samples
        - Visualization of microbial abundances (stacked bars, etc.)
        - Comparison of the abundance of a single microbe across samples
        - Testing for significant differences in organism abundances
          between groups of samples
    """

    id = "microbiome-explorer"
    subtitle = "Microbiome Explorer"

    children = [

        wist.StExpander(
            id="data",
            label="Input Data",
            expanded=True,
            children=[
                MicrobiomeAbund(id="abund"),
                wist.StDataFrame(
                    id="annots",
                    label="Sample Annotations",
                    kwargs=dict(index_col=0)
                ),
                wist.StDownloadDataFrame(
                    target="annots",
                    label="Download Annotations"
                )
            ]
        ),
        wist.StDuplicator(
            id='plots',
            children=[
                deepcopy(wist.StSelector(
                    id=f"plot_{i}",
                    disable_sidebar=True,
                    options=[
                        Ordination(id="ordination")
                    ]
                ))
                for i in range(20)
            ],
            value=[True] + [False for _ in range(19)]
        )
    ]

    requirements = [
        "scikit-learn"
    ]

    def msg(self, msg):
        """Write to the message container."""
        self.main_container.write(msg)

    def abund(self, level=None) -> pd.DataFrame():
        """
        Return the abundance table
        """

        # Get the abundances
        abund = self.get(["data", "abund"])

        if abund.shape[0] == 0:
            return

        # If the level is not specified
        if level is None:
            # Return everything
            pass

        # If a level is specified
        else:

            # Get the taxonomic information for each row
            index_orgs = self.get(["data", "abund"], attr="index_orgs")

            # Filter down to the rows which are assigned at that level
            abund = abund.reindex(
                index=index_orgs.query(
                    f"level == '{level}'"
                ).index
            )

            if abund.shape[0] == 0:
                msg = f"No organisms classified at the {level} level"
                raise WidgetFunctionException(msg)

        return abund

    def abund_hash(self) -> pd.DataFrame():
        """
        Return the hash of the abundance table
        """

        return self.get(["data", "abund"], attr="hash")

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

    def update_options(self):
        """Update the menu selection items based on the user inputs."""

        # Get the sample annotations provided by the user
        annots = self.sample_annotations()

        # If none were provided
        if annots is None:
            # Take no action
            return

        # Update the Ordination plots
        for ord in self._find_child("ordination"):

            ord.update_options(list(annots.columns.values))

    def run_self(self):

        self.update_options()

        self.clone_button(sidebar=True)


if __name__ == "__main__":
    w = MicrobiomeExplorer()
    w.run()
