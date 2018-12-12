import json
import sys
import logging
import requests
import bs4
import pandas as pd
import re

import cleaning_functions

# Get config values.
with open('config.json', 'r') as f:
    config = json.load(f)

# Setup logging.
path = config['PATHS']['ERROR_LOG']
logging.basicConfig(filename = path, filemode = 'w', level = logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_soup(url):
    """Request url and convert response to strained BeautifulSoup object."""
    # Request the url and raise an exception if something strange returned.
    response = requests.get(url, headers = config['HEADERS'])
    if response.status_code != 200:
        msg = url + ' gave status code ' + response.status_code
        print(msg)
        logging.warning(msg)
        raise Exception
    # Limit parsing to only <h1> tags or the tag <div id='tabcontwrap'>.
    strainer = bs4.SoupStrainer(
        lambda name, attrs: name == 'h1' or attrs.get('id') == 'tabcontwrap'
    )
    # Parse response text into a BeautifulSoup object.
    soup = bs4.BeautifulSoup(
        markup = response.text, features = "lxml", parse_only = strainer
    )
    return soup


def get_school(school_id):
    """Get six pages of data associated with a CollegeData.com school_id and
    return a pandas Series object holding extracted values.
    """
    school_series = pd.Series(name = school_id)
    for page_id in range(1, 7):
        # Request and convert page to soup object.
        url = config['URL']['PART1'] + str(page_id) \
                + config['URL']['PART2'] + str(school_id)
        soup = get_soup(url)
        # Raise an error if the <h1> tag contained the empty page string.
        if soup.h1.string == config['EMPTY_H1']:
            msg = 'School ID ' + str(school_id) + ' has no info.'
            print(msg)
            logging.info(msg)
            raise IOError

        # Cleaning soup and extract values as series.
        print(f'Extracting school {school_id}, page {page_id}.')
        soup = cleaning_functions.clean(soup, page_id)

        # Extract data.
        school_series = school_series.append(extract(soup))
    
    return school_series


def extract(soup):
    """Extract data from tables in BeautifulSoup object as a pandas Series."""
    s = pd.Series()
    # Convert all HTML tables in page to a list of pandas DataFrames.
    df_list = pd.read_html(soup.decode(), na_values = config['NA_VALS'], index_col = 0)

    # Split dfs into separate lists depending on dimension.
    onecol_df_list = []
    table_df_list = []
    for df in df_list:
        if len(df.columns) == 1:
            onecol_df_list.append(df)
        if len(df.columns) > 1:
            table_df_list.append(df)

    # DATAFRAMES w/ONE COLUMN
    ##########################################################################
    # Extract only column from each df in one_col_df_list as a Series.
    onecol_s_list = [df.iloc[:, 0] for df in onecol_df_list]
    if onecol_s_list:
        onecol_s = pd.concat(onecol_s_list)
        s = s.append(onecol_s)

    # DATAFRAMES w/MULTIPLE COLUMNS
    ##########################################################################
    for df in table_df_list:
        # TABLES WITH UNIQUE VALUES
        # 'High School Units Required or Recommended' table on 'Admissions' 
        # page, and 'Examinations' table, also on 'Admissions' page, have the 
        # same structure. Create Series from cell vals each labeled by 
        # combining row + column label.
        if df.index.name in ['Subject', 'Exam']:
            table_s = pd.Series()
            cols_s = [df[col] for col in df.columns]
            for col_s in cols_s:
                col_s = col_s[col_s.index.notna()] # drop null index rows
                if col_s.name.find('Unnamed') == -1:
                    col_s.index = col_s.index + ', ' + col_s.name
                table_s = table_s.append(col_s)
            s = s.append(table_s)

        # CATEGORICAL TABLES
        # 'Selection of Students' tables exist on 'Overview' and 
        # 'Admissions' page. Each row only contains only up to a single 'X' 
        # under one of the columns. Create a Series of the marked column label
        # for each row.
        if df.index.name == 'Factor':
            table_s = pd.Series()
            for row_name, row in df.iterrows():
                label = df.index.name + ', ' + row_name
                vals = row.dropna().index.tolist()
                if vals:
                    val = vals[0]
                    table_s[label] = val
            s = s.append(table_s)

        # 'Intercollegiate Sports Offered' exists on the 'Campus Life'
        # page. It is similar to the previous 'Selection of Students'
        # table, but we will extract values by column instead of by row.
        # Also, multiple rows can be marked, so our Series values will be 
        # a list of marked row labels.
        if df.index.name == 'Intercollegiate Sports Offered':
            table_s = pd.Series()
            for col in df.columns:
                label = df.index.name + ', ' + col
                vals = df[col].dropna().index.tolist()
                if vals:
                    table_s[label] = tuple(vals)
            s = s.append(table_s)

    return s


def convert_to_float(s):
    # Try to convert 'str' to 'float', if possible.
    converted_s = pd.Series(name = s.name)
    for label, val in s.items():
        try:
            converted_s[label] = float(val)
        except:
            converted_s[label] = val
    return converted_s    

            
def remove_duplicates(s):
    # Remove trivial duplicates; raise error if non-trivial duplicates exist.
    s = s.dropna()
    idx_first_dups = s.index.duplicated(keep = 'first')
    idx_last_dups = s.index.duplicated(keep = 'last')
    first_dups = s[idx_first_dups].sort_index()
    last_dups = s[idx_last_dups].sort_index()
    mask = first_dups != last_dups
    dups = first_dups[mask].append(last_dups[mask])
    if not dups.empty:
        logging.warning('Duplicate values: ' + str(dups))
        raise Exception
    school_series = s[~idx_last_dups] # keep only first instances of dups
    return s


def main():
    # Get start and stop school IDs from user or defaults from config file.
    try:
        if len(sys.argv) > 1:
            start_school_id = int(sys.argv[1])
        else:
            start_school_id = config['SCHOOL_ID']['START']
        if len(sys.argv) > 2:
            end_school_id = int(sys.argv[2])
        else:
            end_school_id = config['SCHOOL_ID']['END']
    except ValueError:
        print('School IDs must be integers.')
        raise

    # Get data for each school and export to .csv file.
    try:
        school_series_list = []
        for school_id in range(start_school_id, end_school_id + 1):
            try:
                school_series = get_school(school_id)
                if school_series is not None:
                    school_series.name = school_id

                    # Try to convert 'str' to 'float', if possible.
                    school_series = convert_to_float(school_series)

                    # Remove trivial duplicates; raise error if non-trivial 
                    # duplicates exist.
                    school_series = remove_duplicates(school_series)

                    school_series_list.append(school_series)
            except IOError:
                pass
    except KeyboardInterrupt:
        print('Stopping...')
    except Exception as e:
        msg = f'ERROR: Exception encountered.'
        logging.critical(msg, exc_info = True)
    else:
        print('Successfully finished.')
    finally:
        df = pd.DataFrame(school_series_list)
        path = config['PATHS']['CSV']
        df.to_csv(path)
        print(f'Scraped {len(df)} schools to {path}')


if __name__ == '__main__':
    main()