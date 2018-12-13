import json
import sys
import logging
import requests
import bs4
import pandas as pd

import collegedatascraper.reformatters

# Get config values.
with open('config.json', 'r') as f:
    config = json.load(f)

# Setup logging.
path = config['PATHS']['ERROR_LOG']
logging.basicConfig(filename=path, filemode='w', level=logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_soup(url):
    """Request url and convert response to strained BeautifulSoup object."""
    # Request the url and raise an exception if something strange returned.
    response = requests.get(url, headers=config['HEADERS'])
    if response.status_code != 200:
        msg = url + ' gave status code ' + response.status_code
        logging.warning(msg)
        raise IOError
    # Limit parsing to only <h1> tags or the tag <div id='tabcontwrap'>.
    strainer = bs4.SoupStrainer(
        lambda name, attrs: name == 'h1' or attrs.get('id') == 'tabcontwrap'
    )
    # Parse response text into a BeautifulSoup object.
    soup = bs4.BeautifulSoup(
        markup=response.text, features="lxml", parse_only=strainer
    )
    return soup


def get_school(school_id):
    """Get six pages of data associated with a CollegeData.com school_id and
    return a pandas Series object holding extracted values.
    """
    school_series = pd.Series(name=school_id)

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
        soup = collegedatascraper.reformatters.reformat(soup, page_id)

        # Extract data and append to school Series.
        s = extract(soup)
        school_series = school_series.append(s)

    school_series = school_series.sort_index()

    # Drop duplicate indices and their values.
    school_series = school_series[~school_series.index.duplicated()]

    school_series.name = school_id

    return school_series


def extract(soup):
    """Extract vals from <table> in BeautifulSoup and return pandas Series."""
    s = pd.Series()

    # Convert <table> to pandas DataFrames.
    df_list = pd.read_html(
        soup.decode(), na_values=config['NA_VALS'], index_col=0
    )

    # Separate <table> with single <td> from those with multiple <td>.
    table_dfs = []
    for df in df_list:
        # Extract values from <table> with only one <td> row as labeled Series.
        if len(df.columns) == 1:
            s = s.append(df.iloc[:, 0])
        # Make list of <table> with multiple columns of <td>.
        if len(df.columns) > 1:
            df = df.loc[df.index.dropna()]  # Drop NaN in index.
            table_dfs.append(df)

    # Extract values from <table> with more than one <td> column.
    for i in range(len(table_dfs)):
        table_s = pd.Series()
        df = table_dfs[i]
        # The 'Subject' and 'Exam' tables are similar.
        if df.index.name in ['Subject', 'Exam']:
            for col in df.columns:
                col_s = df[col]
                col_s.index = df.index.name + ', ' + col_s.index + ', ' + col
                table_s = table_s.append(col_s)
        # The 'Factor' and 'Sports' tables are similar, if you transpose one.
        if df.index.name in ['Factor', 'Intercollegiate Sports Offered']:
            if df.index.name == 'Factor':
                df = df.T  # Rotate this table and extract cols as vals.
                df.index.name = 'Factor'
            for col in df.columns:
                label = df.index.name + ', ' + col
                vals = df[col].dropna().index.tolist()
                if vals:
                    if df.index.name == 'Intercollegiate Sports Offered':
                        table_s[label] = tuple(vals)  # Has many vals.
                    elif df.index.name == 'Factor':
                        table_s[label] = vals[0]  # Has only one val.
        s = s.append(table_s)
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

    # Get data for each school and export to .csv file, in chunks.
    s_list = []
    try:
        for school_id in range(start_school_id, end_school_id + 1):
            try:
                s = get_school(school_id)
            except (IOError, KeyError):
                msg = f'Failed while processing school {school_id}.'
                logging.warning(msg)
                print(msg)
            else:
                print(f'Successfully scraped school {school_id}.')
                s_list.append(s)
    except KeyboardInterrupt:
        print('Stopping...')
    except Exception as e:
        msg = f'CRITICAL: Exception encountered.\n{e}'
        logging.critical(msg, exc_info=True)
    else:
        print('Successfully finished.')
    finally:
        # Write DataFrame df to CSV located at path.
        df = pd.DataFrame(s_list)
        df.index = df.index.rename('School ID')
        path = config['PATHS']['CSV']
        df.to_csv(path, index_label='School ID')


if __name__ == '__main__':
    main()
