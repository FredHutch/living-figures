"""
Utilities needed for processing REBASE data.
"""

from typing import Union
from widgets.base.helpers import parse_dataframe_string
from widgets.base.helpers import encode_dataframe_string
import pandas as pd
from widgets.streamlit.resource.files.base import StFile
from widget_store.bio.rebase.utilities.parse_rebase import parse_rebase


class StREBASE(StFile):
    """Process epigenetic data from REBASE format."""

    value = pd.DataFrame()

    def __init__(
        self,
        id="rebase",
        value=None,
        label="REBASE Files",
        help: Union[str, None] = None,
        disabled: bool = False,
        label_visibility: str = "visible",
        sidebar=True,
        show_uploader=True,
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
            StREBASE:       The instantiated resource object.
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
            **kwargs
        )

    def parse_files(self, files):
        """Parse any tabular data files uploaded by the user."""

        # Read in each of the files and add them to
        # the existing data
        for file in files:

            if file is not None:
                genome_name = file.name

                for suffix in [".txt"]:
                    if genome_name.endswith(suffix):
                        genome_name = genome_name[:-len(suffix)]

                # Try to read the file
                try:
                    enzymes = parse_rebase(file)
                    pass
                except Exception as e:
                    self.main_container.warning(
                        f"Could not read file ({file})\n{str(e)}"
                    )

                # Add it to the table, overwriting
                # any other data for the same genome
                self.add_genome_data(enzymes, genome_name)

    def add_genome_data(self, enzymes: pd.DataFrame, genome_name: str):

        # If the existing table does not have any data
        if self.get_value().shape[0] == 0:

            # Just add the data
            self.set_value(enzymes.assign(genome=genome_name))

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
                    enzymes.assign(genome=genome_name)
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
