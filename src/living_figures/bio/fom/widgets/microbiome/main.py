import pandas as pd
from living_figures.bio.fom.widgets.microbiome import MicrobiomeAbund
from living_figures.bio.fom.widgets.microbiome import Ordination
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
    title = "Microbiome Explorer"

    children = [

        wist.StExpander(
            id="data",
            label="Input Data",
            expanded=True,
            children=[
                MicrobiomeAbund(id="abund")
            ]
        ),
        wist.StDuplicator(
            id='plots',
            children=[
                wist.StSelector(
                    id=f"plot_{i}",
                    disable_sidebar=True,
                    options=[
                        Ordination(id="ordination")
                    ]
                )
                for i in range(20)
            ]
        )
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

    def run_self(self):

        self.clone_button(sidebar=True)


if __name__ == "__main__":
    w = MicrobiomeExplorer()
    w.run()
