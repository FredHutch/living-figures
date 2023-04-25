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
        self.value = pd.read_csv(
            uploaded_file,
            index_col=0,
            sep="\t" if "tsv" in uploaded_file.name else ",",
            compression="gzip" if uploaded_file.name.endswith(".gz") else None
        )

        # Parse the index column as a taxonomic label
        self.index_orgs = self.parse_index_orgs()

        # Normalize the organism names using the 'path' from index_orgs
        self.value = self.value.rename(
            index=self.index_orgs['path'].get
        )
        self.index_orgs = self.index_orgs.rename(
            index=self.index_orgs['path'].get
        )

        # Sum up counts for ancestors, if needed
        self.populate_anc_counts()

        # Compute the hash of the data
        self.hash = md5(self.value.to_csv().encode()).hexdigest()

        shape = self.value.shape
        msg = f"Read {shape[0]:,} organisms and {shape[1]:,} samples"
        self._root().msg(msg)

    def populate_anc_counts(self):
        """Populate counts for ancestors, if needed."""

        # Only compute sums for count (integer) data
        if not self.value.applymap(lambda v: isinstance(v, int)).all().all():
            # Take no action
            return

        # If there are any samples which have more reads assigned
        # to a child node than are assigned to its parent
        if self.should_populate_anc_counts():

            # Add back any missing ancestors which did not have reads assigned
            self.populate_missing_ancestors()

            # Sum up reads from children to parent
            self.value = self.value.apply(
                lambda c: self.populate_anc_counts_col(c)
            )

    def populate_missing_ancestors(self):
        """Add back any missing ancestors which did not have reads assigned."""

        current_taxa = set(self.index_orgs.index.values)
        all_taxa = set([
            anc
            for path in self.index_orgs.index.values
            for anc in self.generate_ancestors(path)
        ])
        missing_ancestors = list(all_taxa - current_taxa)

        if len(missing_ancestors) > 0:

            self.value = pd.concat([
                self.value,
                pd.DataFrame(
                    index=missing_ancestors,
                    columns=self.value.columns
                ).fillna(0)
            ])

            self.index_orgs = pd.concat([
                self.index_orgs,
                pd.DataFrame([
                    parse_tax_string(org_str)
                    for org_str in missing_ancestors
                ], index=missing_ancestors)
            ])

    def generate_ancestors(self, path: str):
        path = path.split("|")
        for i in range(1, len(path)+1):
            yield '|'.join(path[:i])

    def should_populate_anc_counts(self):
        """
        Check to see if there are any samples for which a child node
        has more reads assigned than its parent does.
        """

        # Iterate over the columns
        for _, cvals in self.value.items():

            # Get the sum of the reads assigned to all children
            # at each node
            child_vals = self.sum_up_child_counts(cvals)

            # If any of the child counts are greater than the parents
            if (cvals < child_vals).any():

                # Than we should populate ancestor counts
                return True

    def sum_up_child_counts(self, cvals):
        """
        Return the Series of counts for all of the reads which are assigned
        at a level below the indicated organism.
        """

        return pd.Series(
            [
                cvals.loc[
                    [
                        child.startswith(anc) and not anc.startswith(child)
                        for child in cvals.index.values
                    ]
                ].sum()
                for anc in cvals.index.values
            ],
            index=cvals.index.values
        )

    def populate_anc_counts_col(self, col: pd.Series):
        """Populate counts for ancestors, if needed, processing a single sample."""

        # For each organism, sum up the counts for all children
        child_counts = self.sum_up_child_counts(col)

        # Add in the values for the child as well
        return col + child_counts

    def parse_index_orgs(self):
        """
        Parse the taxonomic information of the index in the abundance table.
        """

        return pd.DataFrame([
            parse_tax_string(org_str)
            for org_str in self.value.index.values
        ], index=self.value.index)


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
