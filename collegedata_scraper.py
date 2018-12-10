# CollegeData scraper.
import numpy as np
import pandas as pd
from requests import get
from bs4 import BeautifulSoup, SoupStrainer
import re


# DEFINITIONS
##############################################################################
# The URLs of interest on collegedata.com are broken down like this:
URL_PT_1 = "https://www.collegedata.com/cs/data/college/college_pg0"
# followed by a `school_id` number. Following that, there is:
URL_PT_2 = "_tmpl.jhtml?schoolId="
# Finally, there is a `page_id` number, ranging from 1 to 6, inclusive.
# Not all possible `school_id` numbers corresponds to a school, but most do.
# A page requested corresponding to a `school_id` with no school data will
# load a page that has a <h1> tag heading with this string:
EMPTY_H1_HEADING = "Retrieve a Saved Search"
# At larger `school_id` values, especially over 1000, no-school pages are
# returned more often. I'm fairly confident there are none over 5000.
SCHOOL_ID_START = 1
SCHOOL_ID_END = 10
# CollegeData.com has no problem with requests without headers, but we can
# send a fake header anyway:
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14) "
           "AppleWebKit/605.1.15 (KHTML, like Gecko) "
           "Version/12.0 Safari/605.1.15"}
# Finally, we'll export our scraped data to a CSV. The scraper will check
# if the CSV already exists, and if so, will adjust the `SCHOOL_ID_START` to
# begin with the `school_id` after the highest already scraped in the CSV:
PATH = "test_scraped.csv"


# SCRAPING FUNCTIONS
##############################################################################
def get_soup(url, SoupStrainer = None):
    # Request page and check if page returned.
    result = get(url, headers = HEADERS)
    if result.status_code != 200:
        raise PageRequestError
    # Parse page text into BeautifulSoup object.
    soup = BeautifulSoup(result.text, "lxml", parse_only = SoupStrainer)
    return soup

def get_collegedata_page(school_id, page_id):
    url = URL_PT_1 + str(page_id) + URL_PT_2 + str(school_id)
    strainer = SoupStrainer(
        lambda tag, d: tag == 'h1' or d.get('id') == 'tabcontwrap')
    soup = get_soup(url, strainer)
    return soup


school_id = 59
# Get each of the six pages for a school.
pages = [get_collegedata_page(school_id, i) for i in range(1, 7)]

# Hold all scraped values in a single pandas Series.
school_s = pd.Series(name = school_id)

# Get the school Name and Description from the first page.
# These values are the only we'll be extracted that are not
# found inside an HTML table.
school_s['Name'] = pages[0].h1.text
school_s['Description'] = pages[0].p.text

# GET DATAFRAMES FROM SCRAPED PAGES
##############################################################################
# Convert all HTML tables as a list of DataFrame objects.
na_vals = ['Not reported', 'Not Reported']
df_list = []
for page in pages:
    dfs = pd.read_html(page.decode(), na_values = na_vals, index_col = 0)
    for i in range(len(dfs)):
        dfs[i] = dfs[i][dfs[i].index.notnull()]  # del rows w/ null indices
    df_list += dfs

# Split all DataFrames into separate lists depending on num of cols and rows.
nocol_df_list  = [df for df in df_list if len(df.columns)==0]
onecol_df_list = [df for df in df_list if len(df) > 1 and len(df.columns)==1]
table_df_list   = [df for df in df_list if len(df.columns)>1]


# EXTRACT FROM DATAFRAMES WITH NO COLUMNS
##############################################################################
# Create a labeled Series from scalar objects and append it to school_s.
vals = [df.index.tolist()[0] for df in nocol_df_list]
idx = ['Entrance Difficulty', 
       "Master's Degrees Offered", 
       "Doctoral Degrees Offered"]
s = pd.Series(vals, index = idx)
school_s = school_s.append(s)


# EXTRACT FROM DATAFRAMES WITH ONE COLUMN, MULTIPLE ROWS
##############################################################################
# Extract first (and only) column from each df in one_col_df_list as a Series.
s_list = [df.iloc[:, 0] for df in onecol_df_list]
s = pd.concat(s_list)
school_s = school_s.append(s)


# EXTRACT FROM DATAFRAMES WITH MULTIPLE COLUMNS
##############################################################################
# 'High School Units Required or Recommended' table on 'Admissions' page, and
# 'Examinations' table, also on 'Admissions' page, have the same structure.
# Create Series from cell vals each labeled by combining row + column label.
results = [df for df in table_df_list if df.index.name in ['Subject', 'Exam']]
for df in results:
    cols_s = [df[col] for col in df.columns]
    for col_s in cols_s:
        col_s.index = col_s.index + ', ' + col_s.name
    s = pd.concat(cols_s)
    school_s = school_s.append(s)

# 'Selection of Students' tables exist on 'Overview' and 'Admissions' page.
# The second one is the full version we will use. Each row only contains only
# up to a single 'X' under one of the columns. Create a Series of the marked
# column label for each row.
results = [df for df in table_df_list if df.index.name == 'Factor']
df = results[1] # Only use the second, full table.

s = pd.Series(index = df.index)
for row_name, row in df.iterrows():
    s[row_name] = row.dropna().index.tolist()[0]
school_s = school_s.append(s)

# 'Intercollegiate Sports Offered' exists on the 'Campus Life' page.
# It is similar to the previous 'Selection of Students' table, but
# we will extract values by column instead of by row. Also, multiple rows
# can be marked, so our Series values will be a list of marked row labels.
col_level_names = ['Sport', 'Offered']
results = [df for df in table_df_list if df.columns.names == col_level_names]
df = results[0] # Should only be one result.

# Manually simplify the column names.
df.columns = ['Sports, Women, Scholarships Given',
              'Sports, Women, Offered',
              'Sports, Men, Scholarships Given',
              'Sports, Men, Offered']
s = pd.Series(index = df.columns)
for col_name in df.columns:
    s[col_name] = df[col_name].dropna().index.tolist()
school_s = school_s.append(s)


# GET ADDITIONAL VALUES
##############################################################################
# Get the FAFSA code.
div = pages[2].find('div', id='section10')
if div:
    tables = div.find_all('table')
    if len(tables) == 3:
        school_s['FAFSA Code'] = tables[2].tbody.th.text[-6:]
        
# Get the list of majors and programs of study.
caption_strings = ['Undergraduate Majors',
                   "Master's Programs of Study",
                   'Doctoral Programs of Study']
for caption_string in caption_strings:
    caption = pages[3].find('caption', string=re.compile(caption_string))
    if caption:
        th = caption.find_next('th')
        td = caption.find_next('td')
        th_string = "---".join(th.stripped_strings)
        td_string = "---".join(td.stripped_strings)
        vals = th_string.split('---')
        vals += td_string.split('---')
        school_s[caption_string] = vals


# CLEANING LABELS
##############################################################################
# Fix city Population labels (varying label contains city name).
idxs = [idx for idx in school_s.index if idx.find('Population') != -1]
if idxs:
    idx = idxs[0]
    school_s['City Population'] = school_s[idx].iloc[0]
    school_s = school_s.drop(idx)
    
# Drop the accuweather javascript map widget.
idxs = [idx for idx in school_s.index if idx.find('View Larger Map') != -1]
if idxs:
    school_s = school_s.drop(idxs[0])