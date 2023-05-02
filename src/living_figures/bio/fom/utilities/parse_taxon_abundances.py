from living_figures.bio.fom.utilities import parse_tax_string
from typing import Tuple
import pandas as pd


def parse_taxon_abundances(
    df: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Parse a table of taxonomic abundances.
    The index must be taxonomic labels (paths).
    Each column is a sample.
    Values can be integers or floats.
    If values are integers and parent values are not
    inclusive of child values, the value of each node
    will be added to the summed value of all child nodes.
    """

    # Parse the index column as a taxonomic label
    index_orgs = parse_index_orgs(df)

    # Normalize the organism names using the 'path' from index_orgs
    df = df.rename(index=index_orgs['path'].get)
    index_orgs = index_orgs.rename(index=index_orgs['path'].get)

    # Sum up counts for ancestors, if needed
    return populate_anc_counts(df, index_orgs)


def populate_anc_counts(df: pd.DataFrame, index_orgs: pd.DataFrame):
    """Populate counts for ancestors, if needed."""

    # Only compute sums for count (integer) data
    if not df.applymap(lambda v: isinstance(v, int)).all().all():
        # Take no action
        pass

    # If there are any samples which have more reads assigned
    # to a child node than are assigned to its parent
    if should_populate_anc_counts(df):

        # Add back any missing ancestors which did not have reads assigned
        df, index_orgs = populate_missing_ancestors(df, index_orgs)

        # Sum up reads from children to parent
        df = df.apply(
            lambda c: populate_anc_counts_col(c)
        )

    return df, index_orgs


def populate_missing_ancestors(df, index_orgs):
    """Add back any missing ancestors which did not have reads assigned."""

    current_taxa = set(index_orgs.index.values)
    all_taxa = set([
        anc
        for path in index_orgs.index.values
        for anc in generate_ancestors(path)
    ])
    missing_ancestors = list(all_taxa - current_taxa)

    if len(missing_ancestors) > 0:

        df = pd.concat([
            df,
            pd.DataFrame(
                index=missing_ancestors,
                columns=df.columns
            ).fillna(0)
        ])

        index_orgs = pd.concat([
            index_orgs,
            pd.DataFrame([
                parse_tax_string(org_str)
                for org_str in missing_ancestors
            ], index=missing_ancestors)
        ])

    return df, index_orgs


def generate_ancestors(path: str):
    path = path.split("|")
    for i in range(1, len(path)+1):
        yield '|'.join(path[:i])


def should_populate_anc_counts(df):
    """
    Check to see if there are any samples for which a child node
    has more reads assigned than its parent does.
    """

    # Iterate over the columns
    for _, cvals in df.items():

        # Get the sum of the reads assigned to all children
        # at each node
        child_vals = sum_up_child_counts(cvals)

        # If any of the child counts are greater than the parents
        if (cvals < child_vals).any():

            # Than we should populate ancestor counts
            return True

    return False


def sum_up_child_counts(cvals):
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


def populate_anc_counts_col(col: pd.Series):
    """Populate counts for ancestors, if needed, processing a single sample."""

    # For each organism, sum up the counts for all children
    child_counts = sum_up_child_counts(col)

    # Add in the values for the child as well
    return col + child_counts


def parse_index_orgs(df):
    """
    Parse the taxonomic information of the index in the abundance table.
    """

    return pd.DataFrame([
        parse_tax_string(org_str)
        for org_str in df.index.values
    ], index=df.index)
