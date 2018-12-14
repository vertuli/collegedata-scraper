import pandas as pd


def extract_series(df):
    """Returns a pandas Series of all info extracted from a DataFrame."""

    # Remove index, value pairs from DataFrame if index is NaN.
    missing = df.index.isna()
    missing_idx = df[missing].index
    df.drop(missing_idx, inplace=True)

    # Extract a Series from a single col DataFrame.
    if len(df.columns) == 1:
        s = df.iloc[:, 0]

    # Extract a Series from a wide DataFrame with multiple columns.
    if len(df.columns) > 1:
        s = wide_df_to_series(df)

    return s

##############################################################################
# EXTRACTING SERIES FROM WIDE DATAFRAMES FUNCTIONS
##############################################################################


def wide_df_to_series(df):
    """Create a single pandas Series from a list of pandas DataFrames objects
    representing CollegeData.com <table> tags holding multiple columns."""

    # There are only four scraped tables from which we want to extract Series.

    # These two are both 'traditional' tables with cells having various vals.
    if df.index.name in ['Subject', 'Exam']:
        s = multival_wide_df_to_series(df)

    # These two both similarly have cell values that 'mark' a row/col label.
    elif df.index.name in ['Factor', 'Intercollegiate Sports Offered']:

        # These can be processed the same way if 'Factor' table is flipped:
        if df.index.name == 'Factor':
            df = df.T  # Transpose
            df.index.name = 'Factor'

        s = singleval_wide_df_to_series(df)  # Returns a tuple of marked vals.

        # 'Factor' table should only have one val marked, so we'll extract it.
        if df.index.name == 'Factor':
            s = s.str[0]

    # There is one other table (on the Overview) which is a shortened copy of
    # the 'Factor' table, which we can ignore.
    else:
        s = None

    return s


def multival_wide_df_to_series(df):
    """Create a pandas Series from a DataFrame with labeled rows and columns
    and differing values in each 'cell'. The returned Series contains up to
    m x n values 'cell' values from the DataFrame, each indexed by its former
    DataFrame row label comma seperated from its column label.
    label"""

    s = pd.Series()

    for col in df.columns:
        col_s = df[col]
        col_s.index = df.index.name + ', ' + col_s.index + ', ' + col
        s = s.append(col_s)

    return s


def singleval_wide_df_to_series(df):
    """Creates a pandas Series from a DataFrame with labeled rows and columns
    but only a single value (or null) in each 'cell' - with this value serving
    to 'mark' a row. The returned Series contains a tuple of all marked row
    labels indexed by the column names."""

    s = pd.Series()

    for col in df.columns:
        # Use the col label + the table index name as the final 'label'.
        key = df.index.name + ', ' + col
        vals = df[col].dropna().index.tolist()  # Marked row label list.
        if vals:
            s[key] = tuple(vals)  # Save multiple marked rows as tuple.

    return s


def main():
    """This function executes if module is run as a script."""


if __name__ == '__main__':
    main()
