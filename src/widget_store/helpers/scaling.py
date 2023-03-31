import pandas as pd


def convert_text_to_scalar(c: pd.Series):
    """Take a column with text or strings and convert to values ranging 0-1."""

    # Get the sorted list of values
    unique_values = c.dropna().drop_duplicates().sort_values()

    # Assign each value to an index position
    value_map = pd.Series(dict(zip(unique_values, range(len(unique_values)))))

    # Set the maximum value at 1
    value_map = value_map / value_map.max()

    # Map NaN to 0
    return c.apply(value_map.get)
