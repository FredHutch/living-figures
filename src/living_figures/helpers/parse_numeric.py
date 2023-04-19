import pandas as pd


def parse_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert any column to numeric which does not change the number of nulls.
    """

    for cname in df.columns.values:
        if is_numeric(df[cname]):
            df[cname] = df[cname].apply(pd.to_numeric, errors='coerce')

    return df


def is_numeric(r: pd.Series) -> bool:
    """Whether a column is numeric (after nulls are dropped)."""

    numeric_vals = r.apply(pd.to_numeric, errors='coerce')
    new_nonnull = numeric_vals.dropna().shape[0]
    return new_nonnull > 0 and new_nonnull == r.dropna().shape[0]
