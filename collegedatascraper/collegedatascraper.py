import json
import requests
import bs4
import logging
import pandas as pd

from collegedatascraper.reformatters import reformat_soup
from collegedatascraper.extractors import extract_series

##############################################################################
# CONFIGURATION
##############################################################################


with open('config.json', 'r') as f:
    config = json.load(f)

url_pt1 = config['URL']['PART1']
url_pt2 = config['URL']['PART2']
headers = config['HEADERS']
empty_h1_string = config['EMPTY_H1']
na_vals = config['NA_VALS']

# Setup logging.
log_path = config['PATHS']['ERROR_LOG']
logging.basicConfig(filename=log_path, filemode='w', level=logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.WARNING)

##############################################################################
# GENERAL SCRAPING FUNCTIONS
##############################################################################


def scrape(start=None, end=None, silent=False):
    """Returns a pandas DataFrame of school information extracted from the
    website CollegeData.com, with each row corresponding to a successfully
    scraped schoolId in the range [start, stop], inclusive, with each column
    corresponding to labeled information fields on the website.

    Notes
    -----
    CAUTION: Without any start or end parameters provided, will use the
    default parameters provided in config.json, which could scrape thousands
    of schoolIds and take hours.

    'scrape' logs errors to a file located at a path defined in config.json.

    Parameters
    ----------
    start : integer
        schoolId from where to begin scraping CollegeData.com. If none
        provided, defaults to the value defined in config.json. If start is
        provided but end is not, will scrape only the start schoolId.
    end : integer
        schoolId to end the scraping, inclusive. If both start and end are
        not provided, end defaults to value defined in config.json.
    silent: boolean, default False
        Suppress success/failure notifications that print for each schoolId,
        as well as any other error messages.

    Returns
    -------
    df : DataFrame

    Examples
    --------
    Getting a DataFrame of college data from a single schoolId.

    >>> df = collegedatascraper.scrape(59)
    Successfully scraped school 59.
    >>> df.info()
    Successfully scraped school 59.
    <class 'pandas.core.frame.DataFrame'>
    Int64Index: 1 entries, 59 to 59
    Columns: 290 entries, 2016 Graduates Who Took Out Loans to Work-Study ...
    dtypes: float64(67), object(223)
    memory usage: 2.3+ KB

    Getting a DataFrame of college data from a range of schoolIds.

    >>> df = collegedatascraper.scrape(1, 10)
    No info exists on CollegeData.com for schoolId 1.
    No info exists on CollegeData.com for schoolId 2.
    No info exists on CollegeData.com for schoolId 3.
    No info exists on CollegeData.com for schoolId 4.
    No info exists on CollegeData.com for schoolId 5.
    Successfully scraped schoolId 6.
    Successfully scraped schoolId 7.
    Successfully scraped schoolId 8.
    Successfully scraped schoolId 9.
    Successfully scraped schoolId 10.
    >>> df.info()
    <class 'pandas.core.frame.DataFrame'>
    Int64Index: 5 entries, 6 to 10
    Columns: 293 entries, 2016 Graduates Who Took Out Loans to Work-Study ...
    dtypes: float64(41), object(252)
    memory usage: 11.5+ KB
    """

    start_id, end_id = get_range(start, end)

    s_list = []
    try:
        for school_id in range(start_id, end_id + 1):
            s = scrape_school(school_id, silent=silent)
            if s is not None:
                s_list.append(s)

    except KeyboardInterrupt:
        msg = 'Stopped!'
    except IOError:
        msg = 'Invalid start_id and/or stop_id.'
    except Exception as e:
        msg = f'Exception occured after getting school(s)!\n{e}'
        logging.critical(msg, exc_info=True)
    else:
        msg = 'Successfully finished!'
    finally:
        if s_list:
            # Create pandas DataFrame from list of Series, and name the index.
            df = pd.DataFrame(s_list)
            df.index = df.index.rename('School ID')

            # Reorder the DataFrame columns alphabetically.
            df = df.reindex(columns=sorted(df.columns))

            # FUTURE FEATURE
            ##################################################################
            # This is where it might be best to start 'cleaning' the DataFrame
            # with functions in a new 'cleaners.py' module to, for example,
            # split strings containing multiple numeric values into separate
            # columns of the appropriate type.
            #
            # Much of this has already been done in a 'cleaning' Jupyter
            # notebook in the related college-yield-gap analysis repository:
            # - https://github.com/vertuli/college-yield-gap/

        else:
            df = None

    return df


def scrape_school(school_id, silent=False):
    """Request the six pages of data associated with a CollegeData.com
    school_id and return a pandas Series object holding the extracted values.
    """

    try:
        # Get DataFrames for the <table> on all six pages for the school_id.
        df_list = []
        for page_id in range(1, 7):

            # Request URL for page; convert response to BeautifulSoup object.
            raw_soup = get_soup(school_id, page_id)

            # Reformat the page structure to make it easier to extract values.
            soup = reformat_soup(raw_soup, page_id)

            # Get pandas DataFrames from <table> in soup; add them to df_list.
            df_list += pd.read_html(
                io=soup.decode(),
                na_values=na_vals,
                index_col=0)

        # Get a list of Series extracted from each of the DataFrames.
        s_list = list(map(extract_series, df_list))

        # Merge all Series into one, and sort the index.
        merged_s = pd.concat(s_list).sort_index()

        # Drop duplicate indices and their vals and name the Series.
        s = merged_s[~merged_s.index.duplicated()]
        s.name = school_id

    except IOError:
        s = None
        msg = f'Got anomalous response while requesting schoolId {school_id}.'
        logging.warning(msg)
    except LookupError:
        s = None
        msg = f'No info exists on CollegeData.com for schoolId {school_id}.'
    except Exception as e:
        s = None
        msg = f'Exception while requesting schoolId {school_id}!\n{e}'
        logging.critical(msg, exc_info=True)
    else:
        msg = f'Successfully scraped schoolId {school_id}.'
    finally:
        if not silent:
            print(msg)

    return s

##############################################################################
# INPUT/OUTPUT FUNCTIONS
##############################################################################


def get_range(start_input, end_input):
    """Get start_id and end_id, from params or from defaults in config."""

    if start_input and end_input:
        # Range is defined by the function parameters.
        start_id = start_input
        end_id = end_input

    elif start_input and not end_input:
        # Range is just the one ID.
        start_id = start_input
        end_id = start_input

    elif not start_input and not end_input:
        # Default range w/o params is from the config file.
        start_id = config['SCHOOL_ID']['START']
        end_id = config['SCHOOL_ID']['END']

    elif not start_input and end_input:
        # Scrape from 1 to the end_input.
        start_id = 1
        end_id = end_input

    if start_id > end_id:
        # This doesn't make sense.
        raise IOError

    return start_id, end_id


def get_soup(school_id, page_id):
    """Requests a page from CollegeData.com corresponding to the provided
    school_id and page_id and converts the response to a BeautifulSoup object
    """

    # Build URL
    url = url_pt1 + str(page_id) + url_pt2 + str(school_id)

    # Request the url and raise exception if something strange returned.
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        msg = url + ' gave status code ' + response.status_code
        logging.warning(msg)
        raise IOError

    # Limit HTML parsing to only <h1> tags or the tag <div id='tabcontwrap'>.
    strainer = bs4.SoupStrainer(
        lambda name, attrs: name == 'h1'
        or attrs.get('id') == 'tabcontwrap'
    )

    # Parse response text into a BeautifulSoup object.
    soup = bs4.BeautifulSoup(
        markup=response.text, features="lxml", parse_only=strainer
    )

    # Raise an error if the <h1> tag contained the empty page string.
    # It's not really an error, as it's expected that many school_id will
    # not correspond to a page with actual school information, but this will
    # allow the scraper to skip any further attempts at more pages for this
    # school_id, saving time.
    if soup.h1.string == empty_h1_string:
        msg = 'School ID ' + str(school_id) + ' has no info.'
        logging.info(msg)
        raise LookupError

    return soup


def main():
    """This function executes if module is run as a script."""


if __name__ == '__main__':
    main()
