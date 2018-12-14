import requests
import bs4
import pandas as pd
import logging
import collegedatascraper.reformatters
from collegedatascraper import config

url_pt1 = config['URL']['PART1']
url_pt2 = config['URL']['PART2']
headers = config['HEADERS']
empty_h1_string = config['EMPTY_H1']
na_vals = config['NA_VALS']


def get_soup(school_id, page_id):
    # Request and convert page to soup object.
    url = url_pt1 + str(page_id) + url_pt2 + str(school_id)

    # Request the url and raise exception if something strange returned.
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        msg = url + ' gave status code ' + response.status_code
        logging.warning(msg)
        raise IOError
    # Limit parsing to only <h1> tags or the tag <div id='tabcontwrap'>.
    strainer = bs4.SoupStrainer(
        lambda name, attrs: name == 'h1'
        or attrs.get('id') == 'tabcontwrap'
    )
    # Parse response text into a BeautifulSoup object.
    soup = bs4.BeautifulSoup(
        markup=response.text, features="lxml", parse_only=strainer
    )

    # Raise an error if the <h1> tag contained the empty page string.
    if soup.h1.string == empty_h1_string:
        msg = 'School ID ' + str(school_id) + ' has no info.'
        logging.info(msg)
        raise IOError

    return soup


def get_df_list(school_id, page_id):
    """Get a list of pandas DataFrames representing the <table> contents of
    the six CollegeData.com pages associated with a school_id."""

    # Get BeautifulSoup object representing page HTML content.
    soup = get_soup(school_id, page_id)

    # Standardize some of the anomalous labels and tables in the page.
    reformatted_soup = collegedatascraper.reformatters.reformat(soup, page_id)

    # Get pandas DataFrames from <table> tags and add them to df_list.
    df_list = pd.read_html(
        reformatted_soup.decode(),
        na_values=na_vals,
        index_col=0
    )

    # Remove rows with NaN indices from each DataFrame.
    for i in range(len(df_list)):
        df_list[i] = df_list[i].loc[df_list[i].index.dropna()]

    return df_list


def multi_val_df_to_series(df):
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


def single_val_df_to_series(df):
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


def df_to_series(df_list):
    """Create a single pandas Series from a list of pandas DataFrames objects
    representing CollegeData.com <table> tags holding multiple columns."""
    s_list = []
    for df in df_list:
        # There are only a maximum of four scraped tables we will transform.
        # Two of them can be processed with the same procedure:
        if df.index.name in ['Subject', 'Exam']:
            s = multi_val_df_to_series(df)
            s_list.append(s)
        # The other two can be processed together if one is flipped:
        if df.index.name == 'Factor':
            df = df.T  # Transpose
            df.index.name == 'Factor'
        # Process the remaining two tables:
        if df.index.name in ['Factor', 'Intercollegiate Sports Offered']:
            s = single_val_df_to_series(df)
            if df.index.name == 'Factor':
                s = s.str[0]  # 'Factor' table cols only mark a single val.
            s_list.append(s)

    s = pd.concat(s_list)

    return s
