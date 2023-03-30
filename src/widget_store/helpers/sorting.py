import pandas as pd
from scipy import cluster


def sort_table(df: pd.DataFrame) -> pd.DataFrame:
    """Sort the rows and columns of a table by linkage clustering."""

    return df.iloc[
        reordered_index(df),
        reordered_index(df.T)
    ]


def reordered_index(
    df: pd.DataFrame,
    method="ward",
    metric="euclidean"
):
    """
    Return the list of index positions following linkage clustering.
    """

    return cluster.hierarchy.leaves_list(
        cluster.hierarchy.linkage(
            df.values,
            method=method,
            metric=metric,
        )
    )
