from hashlib import md5
import widgets.streamlit as wist
import pandas as pd
from living_figures.bio.fom.utilities import parse_tax_string


class MicrobiomeAbund(wist.StDataFrame):
    """Read in the abundance values of a microbiome datasets."""

    label = "Abundance Table"
    hash = None
    index_orgs = None

    children = [
        wist.StResource(id='msg')
    ]

    def parse_files(self, uploaded_file):

        # Read the file
        self.value: pd.DataFrame = pd.read_csv(
            uploaded_file,
            index_col=0,
            sep="\t" if "tsv" in uploaded_file.name else ",",
            compression="gzip" if uploaded_file.name.endswith(".gz") else None
        )
        shape = self.value.shape
        msg = f"Read {shape[0]:,} rows and {shape[1]:,} columns"
        self._root().msg(msg)

        # Compute the hash of the data
        self.hash = md5(self.value.to_csv().encode()).hexdigest()

        # Parse the index column as a taxonomic label
        self.index_orgs = self.parse_index_orgs()

    def parse_index_orgs(self):
        """
        Parse the taxonomic information of the index in the abundance table.
        """

        return pd.DataFrame([
            parse_tax_string(org_str)
            for org_str in self.value.index.values
        ], index=self.value.index)
