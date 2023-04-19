"""
Utilities needed for processing PacBio epigenetic motif data.
"""

from typing import Union
from widgets.base.helpers import parse_dataframe_string
from widgets.base.helpers import encode_dataframe_string
import pandas as pd
from widgets.streamlit.resource.files.base import StFile


class StPBMotif(StFile):
    """Process epigenetic data from PacBio motifs.csv format."""

    value = pd.DataFrame()

    cname_map = {
        "Motif": "motifString",
        "Modified Position": "centerPos",
        "Motification Type": "modificationType",
        "% of Motifs Detected": "fraction",
        "# of Motifs Detected": "nDetected",
        "# of Motifs in Genome": "nGenome",
        "Mean QV": "meanScore",
        "Mean Coverage": "meanCoverage",
        "Partner Motif": "partnerMotifString",
        "Mean IPD ratio": "meanIpdRatio",
        "Group Tag": "groupTag",
        "Objective Score": "objectiveScore"
    }

    def __init__(
        self,
        id="pacbio_motif",
        value=None,
        label="PacBio Motifs",
        help: Union[str, None] = None,
        disabled: bool = False,
        label_visibility: str = "visible",
        sidebar=True,
        show_uploader=True,
        cname_map={
            "Motif": "motifString",
            "Modified Position": "centerPos",
            "Motification Type": "modificationType",
            "% of Motifs Detected": "fraction",
            "# of Motifs Detected": "nDetected",
            "# of Motifs in Genome": "nGenome",
            "Mean QV": "meanScore",
            "Mean Coverage": "meanCoverage",
            "Partner Motif": "partnerMotifString",
            "Mean IPD ratio": "meanIpdRatio",
            "Group Tag": "groupTag",
            "Objective Score": "objectiveScore"
        },
        **kwargs
    ):
        """
        Args:
            id (str):       The unique key for the resource.
            label (str):    (optional) Label used for user input display
                            elements.
            help (str):     (optional) Help text used for user input display
                            elements.
            value:          (optional) The starting Pandas DataFrame.
            disabled (bool):  (optional) If True, the input element is
                            disabled (default: False)
            label_visibility: (optional) The visibility of the label.
                            If "hidden", the label doesn't show but there is
                            still empty space for it above the widget
                            (equivalent to label=""). If "collapsed", both
                            the label and the space are removed.
                            Default is "visible"
            sidebar (bool): Set up UI in the sidebar vs. the main container
            show_uploader:  Show / hide the uploader element

        Returns:
            StPBMotif:       The instantiated resource object.
        """

        # Parse the provided value, converting from a gzip-compressed
        # string if necessary
        value = parse_dataframe_string(value)

        # Set up the resource attributes
        super().__init__(
            id=id,
            label=label,
            help=help,
            value=value,
            disabled=disabled,
            label_visibility=label_visibility,
            sidebar=sidebar,
            show_uploader=show_uploader,
            accept_multiple_files=True,
            cname_map=cname_map,
            **kwargs
        )

    def parse_files(self, files):
        """Parse any tabular data files uploaded by the user."""

        # Read in each of the files and add them to
        # the existing data
        for file in files:

            if file is not None:

                # If the user uploaded a CSV
                if file.name.endswith('.csv'):

                    # Read the CSV
                    self.parse_csv(file)

    def parse_csv(self, file):

        # Read the CSV file
        motifs = pd.read_csv(file)

        # Apply the column mappings
        motifs = motifs.rename(
            columns=self.cname_map
        )

        # Make sure that the expected columns are present
        expected_cnames = [
            "motifString",
            "centerPos",
            "modificationType",
            "fraction",
            "nDetected",
            "nGenome",
            "groupTag",
            "partnerMotifString",
            "meanScore",
            "meanIpdRatio",
            "meanCoverage",
            "objectiveScore"
        ]

        missing_cnames = [
            cname
            for cname in expected_cnames
            if cname not in motifs.columns.values
        ]

        # If any of those columns are missing
        if len(missing_cnames) > 0:
            # Warn the user
            msg = f"Did not find expected columns - {', '.join(missing_cnames)} in {file.name}" # noqa
            if self.main_container is not None:
                self.main_container.warning(msg)
            else:
                raise Exception(msg)
            # Take no further action
            return

        # Add a unique ID for the motif + position + modification
        # Also add the motif length
        motifs = motifs.assign(
            text=motifs.apply(
                self.format_motif_text,
                axis=1
            ),
            motif_id=motifs.apply(
                lambda r: f"{r['motifString']}-{r['centerPos']}-{r['modificationType']}", # noqa
                axis=1
            ),
            motif_length=motifs['motifString'].apply(len)
        )

        # If there is a 'genome' column already present, then this CSV must
        # have been downloaded from a previous iteration of the browser
        if 'genome' in motifs.columns.values:

            # Add each of the individual genomes
            for genome_name, genome_motifs in motifs.groupby('genome'):
                self.add_genome_data(genome_motifs, genome_name)

        # If no 'genome' column is present, it must be from a single genome
        else:

            # Get the genome name from the file name
            genome_name = file.name

            # Strip off the standard suffix
            for suffix in [".csv", "motifs", "."]:
                if genome_name.endswith(suffix):
                    genome_name = genome_name[:-len(suffix)]

            # If there is nothing left
            if len(genome_name) == 0:
                # Assign a null value
                genome_name = None

            # Add it to the table, overwriting
            # any other data for the same genome
            self.add_genome_data(motifs, genome_name)

    def format_motif_text(self, r):
        """Format the hovertext field."""

        return "<br>".join([
            f"{k}: {v}" for k, v in r.items()
        ])

    def add_genome_data(
        self,
        motifs: pd.DataFrame,
        genome_name: Union[str, None]
    ):

        # If the genome_name is null
        if genome_name is None:

            # Pick a new genome name following the pattern "Unnamed N"
            genome_name_ix = self.get_value().reindex(
                columns=['genome']
            ).dropna(
            ).drop_duplicates(
            ).shape[0] + 1
            genome_name = f"Unnamed {genome_name_ix}"

        # If the existing table does not have any data
        if self.get_value().shape[0] == 0:

            # Just add the data
            self.set_value(motifs.assign(genome=genome_name))

        # If the existing table does indeed have data
        else:

            # Make sure that there is a 'genome' column
            self.sanity_check_data()

            # Add the new data, removing any other
            # data from the same genome
            self.set_value(
                pd.concat([
                    self.get_value().query(
                        f"genome != '{genome_name}'"
                    ),
                    motifs.assign(genome=genome_name)
                ])
            )

    def sanity_check_data(self):
        """Run some sanity checks on the data table."""

        df = self.get_value()
        msg = f"Expected DataFrame, not {type(df)}"
        assert isinstance(df, pd.DataFrame), msg

        if df.shape[0] > 0:
            msg = "Expected a 'genome' column in the table"
            assert 'genome' in df.columns.values

    def _source_val(self, val, **kwargs):
        """
        Return a string representation of an attribute value
        which can be used in source code initializing this resource.
        The value attribute is a DataFrame which can be serialized
        as a dict of lists.
        That dict of list will be serialized to JSON and compressed
        with zlib to reduce the total file size.
        """

        if isinstance(val, str):
            return f'"{val}"'
        elif isinstance(val, pd.DataFrame):
            return encode_dataframe_string(val)

        else:
            return val
