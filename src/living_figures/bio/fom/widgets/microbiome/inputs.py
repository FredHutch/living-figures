from hashlib import md5
import widgets.streamlit as wist
import pandas as pd
import streamlit as st
from living_figures.bio.fom.utilities import parse_taxon_abundances


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
        df = pd.read_csv(
            uploaded_file,
            index_col=0,
            sep="\t" if "tsv" in uploaded_file.name else ",",
            compression="gzip" if uploaded_file.name.endswith(".gz") else None
        )

        # Parse the table of taxonomic abundances
        self.value, self.index_orgs = self.parse_taxon_abundances(df)

        # Compute the hash of the data
        self.hash = md5(self.value.to_csv().encode()).hexdigest()

        shape = self.value.shape
        msg = f"Read {shape[0]:,} organisms and {shape[1]:,} samples"
        self._root().msg(msg)

    @st.cache_data(max_entries=10)
    def parse_taxon_abundances(_self, df):
        return parse_taxon_abundances(df)


class StHashedDataFrame(wist.StDataFrame):
    """Read in a DataFrame and compute a hash."""

    hash = None

    def parse_files(self, uploaded_file):

        # Read the file
        self.value: pd.DataFrame = pd.read_csv(
            uploaded_file,
            index_col=0,
            sep="\t" if "tsv" in uploaded_file.name else ",",
            compression="gzip" if uploaded_file.name.endswith(".gz") else None
        )

        # Compute the hash of the data
        self.hash = md5(self.value.to_csv().encode()).hexdigest()
