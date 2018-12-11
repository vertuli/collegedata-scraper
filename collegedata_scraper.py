import json
import sys
import logging
import requests
import bs4
import pandas as pd
import re
from inspect import getmembers, isfunction
import cleaning_functions
import extracting_functions
cleaning_function_list = getmembers(cleaning_functions, isfunction)
extracting_functions_list = getmembers(extracting_functions, isfunction)


# Get config values.
with open('config.json', 'r') as f:
    config = json.load(f)

    
# The SoupStrainer limits our HTML results to the <h1> and the content <div>.
def strainer_filter(tag, attrs):
    return tag == 'h1' or attrs.get('id') == 'tabcontwrap'
strainer = bs4.SoupStrainer(strainer_filter)


# Error logging.
logging.basicConfig(
    filename = config['PATHS']['ERROR_LOG'], 
    filemode = 'w', 
    level = logging.DEBUG
)
logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_soup(url):
    # Request page and check if page returned.
    result = requests.get(url, headers = config['HEADERS'])
    if result.status_code != 200:
        msg = url + ' gave status code ' + result.status_code
        print(msg)
        logging.warning(msg)
        raise Exception
    # Parse page text into BeautifulSoup object.
    soup = bs4.BeautifulSoup(result.text, "lxml", parse_only = strainer)
    return soup


def scrape_school(school_id):
    # Extract and combine values from six pages associated w/school_id.
    school_series = pd.Series(name = school_id)
    for page_id in range(1, 7):
        # Request and convert page to soup object.
        url = config['URL']['PART1'] + str(page_id) \
                + config['URL']['PART2'] + str(school_id)
        soup = get_soup(url)
        if soup.h1.string == config['EMPTY_H1']:
            msg = 'School ID ' + str(school_id) + ' has no info.'
            print(msg)
            logging.info(msg)
            raise IOError
        print(f'Extracting school {school_id}, page {page_id}.')
        
        # Use cleaning and extracting functions to get page values.
        for cleaning_func_tuple in cleaning_function_list:
            cleaning_func = cleaning_func_tuple[1]
            soup = cleaning_func(soup)
        page_series = pd.Series()
        for extracting_func_tuple in extracting_functions_list:
            extracting_func = extracting_func_tuple[1]
            extracted_series = extracting_func(soup)
            page_series = page_series.append(extracted_series) 
        school_series = school_series.append(page_series)

        school_series = remove_duplicates(school_series)
    return school_series

            
def remove_duplicates(s):
    # Check for duplicates
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
                school_series = scrape_school(school_id)
                if school_series is not None:
                    school_series.name = school_id
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