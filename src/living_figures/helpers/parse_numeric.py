import pandas as pd


def parse_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert any column to numeric which does not change the number of nulls.
    """

    for cname in df.columns.values:

        numeric_vals = df[cname].apply(pd.to_numeric, errors='coerce')
        new_nonnull = numeric_vals.dropna().shape[0]
        if new_nonnull > 0 and new_nonnull == df[cname].dropna().shape[0]:
            df[cname] = numeric_vals

    return df
