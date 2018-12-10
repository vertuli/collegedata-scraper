# CollegeData scraper.
import numpy as np
import pandas as pd
from requests import get
from bs4 import BeautifulSoup, SoupStrainer
from IPython.display import clear_output
import re


# DEFINITIONS
##############################################################################
# The URLs of interest on collegedata.com are broken down like this:
URL_PT_1 = "https://www.collegedata.com/cs/data/college/college_pg0"
# followed by a `school_id` number. Following that, there is:
URL_PT_2 = "_tmpl.jhtml?schoolId="
# Finally, there is a `page_id` number, ranging from 1 to 6, inclusive.
PAGE_IDS = range(1, 7)
# Not all possible `school_id` numbers corresponds to a school, but most do.
# A page requested corresponding to a `school_id` with no school data will
# load a page that has a <h1> tag heading with this string:
EMPTY_H1 = "Retrieve a Saved Search"
# At larger `school_id` values, especially over 1000, no-school pages are
# returned more often. I'm fairly confident there are none over 5000.
SCHOOL_ID_START = 1
SCHOOL_ID_END = 5000
SCHOOL_IDS = range(SCHOOL_ID_START, SCHOOL_ID_END + 1)
# CollegeData.com has no problem with requests without headers, but we can
# send a fake header anyway:
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14) "
           "AppleWebKit/605.1.15 (KHTML, like Gecko) "
           "Version/12.0 Safari/605.1.15"}
# Missing values are commonly labeled with these strings:
NA_VALS = ['Not reported', 'Not Reported']
# Finally, we'll export our scraped data to a CSV. The scraper will check
# if the CSV already exists, and if so, will adjust the `SCHOOL_ID_START` to
# begin with the `school_id` after the highest already scraped in the CSV:
PATH = "test_scraped.csv"


def get_soup(url, SoupStrainer = None):
    """Gets soup! Checks for a good response, too.
    """
    # Request page and check if page returned.
    result = get(url, headers = HEADERS)
    
    if result.status_code != 200:
        raise PageRequestError
        
    # Parse page text into BeautifulSoup object.
    soup = BeautifulSoup(result.text, "lxml", parse_only = SoupStrainer)
    return soup


def get_collegedata_page(school_id, page_id):
    """Gets a specific CollegeData.com soup, and checks if it is properly 
    formed.
    """
    # Build URL.
    url = URL_PT_1 + str(page_id) + URL_PT_2 + str(school_id)
    
    # The SoupStrainer limits our results to the title and the content div.
    strainer = SoupStrainer(lambda tag, d:
                            tag == 'h1' or d.get('id') == 'tabcontwrap')

    soup = get_soup(url, strainer)
    print(f'Getting {url}')
        
    return soup


def relabel(page):
    """This relabels page tags to avoid data loss due to duplication.
    It also deletes a pesky javascript map that could get later sucked up.
    """
    # Prepend parent labels to the <th> row label tags having class = 'sub'.
    for tag in page.find_all('th', class_ = 'sub'):
        tag_text = tag.get_text(' ', strip = True)
        parent_tag = tag.find_previous('th', class_ = None)
        parent_text = parent_tag.get_text(' ', strip = True)
        tag.string = parent_text + ', ' + tag_text

    # Do the same for tags without class = 'sub' but with tab indents '\xa0':
    regex = re.compile('\xa0')
    for tag in page.find_all('th', string = regex):
        tag.string = tag.get_text(' ', strip = True)
        if tag.string == 'Women':
            header_tag = tag.parent.find_previous('tr').th
        if tag.string == 'Men':
            header_tag = tag.parent.find_previous('tr').find_previous('tr').th
        if header_tag:
            tag.string = header_tag.string + ', ' + tag.string  
            
    # Prepend labels to GPA row labels.
    regex = re.compile('Grade Point Average')
    caption = page.find('caption', string = regex)
    if caption:
        gpa_table = caption.parent
        header_tag = gpa_table.tbody.th
        header_tag.string = 'GPA, Average'
        sub_tags = gpa_table.find_all('th')[1:]
        for tag in sub_tags:
            tag.string = header_tag.string + ', ' + tag.string
            
    # Prepend labels to financial aid information
    div = page.find('div', id = 'section11')
    if div:
        for table in div.find_all('table')[0:2]:
            caption_string = table.caption.get_text(' ', strip = True)
            th_tags = table.find_all('th')
            for tag in th_tags:
                string = caption_string + ', '
                string = string + tag.get_text(' ', strip = True)
                tag.string = string

    # Replace table data cells with links with the link address itself.
    td_tags = page.find_all('td')
    for tag in td_tags:
        link_tag = tag.find('a')
        if link_tag:
            tag.string = link_tag['href']

    # Prepend labels to duplicate E-mail and Web Site labels.
    regex = re.compile('Financial Aid Office')
    caption = page.find('caption', string = regex)
    if caption:
        email_tag = caption.find_next('th', string = 'E-mail')
        email_tag.string = 'Financial Aid Office E-mail'
        website_tag = caption.find_next('th', string = 'Web Site')
        website_tag.string = 'Financial Aid Office Web Site'
        
    # Fix city Population labels (varying label contains city name).
    regex = re.compile('Population')
    th_tag = page.find('th', string = regex)
    if th_tag:
        th_tag.string = "City Population"
        
    # Rename the duplicate Entrance Difficulty label on the Overview page.
    div = page.find('div', id = 'section0')
    if div:
        th_tag = div.find('th', string = 'Entrance Difficulty')
        th_tag.string = 'Entrance Difficulty, Category'
        
    # Prepend labels to 'Other Application Requirements' table.
    caption = 'Other Application Requirements'
    caption_tag = page.find('caption', string = caption)
    if caption_tag:
        th_tags = caption_tag.parent.find_all('th')
        for tag in th_tags:
            text = tag.get_text(' ', strip = True)
            tag.string = 'Application Requirement, ' + text
        
    # Prepend labels to 'Security' table.
    div = page.find('div', id = 'section22')
    if div:
        th_tags = div.find_all('th')
        for tag in th_tags:
            text = tag.get_text(' ', strip = True)
            tag.string = 'Security, ' + text
    
    # Delete the row containing the map widget.
    b_tag = page.find('b', string = 'View Larger Map')
    if b_tag:
        parent_row = b_tag.find_parent('tr')
        parent_row.decompose()
    
    return page


def extract(page):
    """Extract data from the HTML <table> tags inside an input BeautifulSoup4 
    object, 'page', representing one of the six pages associated with a
    school_id on CollegeData.com, using pandas.read_html() to convert tables
    to DataFrames and processing to output the data as a pandas Series object.
    """
    page_s = pd.Series()
    
    # Convert all HTML tables in page to a list of pandas DataFrames.
    if page.find('table'):
        df_list = pd.read_html(page.decode(), na_values = NA_VALS, 
            index_col = 0)
    else:
        df_list = []

    # Split all dfs into separate lists depending on dimension.
    nocol_df_list = []
    onecol_df_list = []
    table_df_list = []
    for df in df_list:
        if len(df.columns) == 1 and len(df) > 1:
            onecol_df_list.append(df)
        if len(df.columns) > 1:
            table_df_list.append(df)

    # DATAFRAMES w/ONE COLUMN
    ##########################################################################
    # Extract only column from each df in one_col_df_list as a Series.
    s_list = [df.iloc[:, 0] for df in onecol_df_list]
    if s_list:
        s = pd.concat(s_list)
        page_s = page_s.append(s)
    
    # DATAFRAMES w/MULTIPLE COLUMNS
    ##########################################################################
    for df in table_df_list:
        # TABLES WITH UNIQUE VALUES
        # 'High School Units Required or Recommended' table on 'Admissions' 
        # page, and 'Examinations' table, also on 'Admissions' page, have the 
        # same structure. Create Series from cell vals each labeled by 
        # combining row + column label.
        if df.index.name in ['Subject', 'Exam']:
            s = pd.Series()
            cols_s = [df[col] for col in df.columns]
            for col_s in cols_s:
                col_s = col_s[col_s.index.notna()] # drop null index rows
                if col_s.name.find('Unnamed') == -1:
                    col_s.index = col_s.index + ', ' + col_s.name
                s = s.append(col_s)
            page_s = page_s.append(s)
            
        # CATEGORICAL TABLES
        # 'Selection of Students' tables exist on 'Overview' and 
        # 'Admissions' page. Each row only contains only up to a single 'X' 
        # under one of the columns. Create a Series of the marked column label
        # for each row.
        if df.index.name == 'Factor':
            s = pd.Series()
            for row_name, row in df.iterrows():
                label = 'Factor, ' + row_name
                vals = row.dropna().index.tolist()
                if vals:
                    val = vals[0]
                    s[label] = val
            page_s = page_s.append(s)

        # 'Intercollegiate Sports Offered' exists on the 'Campus Life'
        # page. It is similar to the previous 'Selection of Students'
        # table, but we will extract values by column instead of by row.
        # Also, multiple rows can be marked, so our Series values will be 
        # a list of marked row labels.
        col_level_names = ['Sport', 'Offered']
        if df.columns.names == ['Sport', 'Offered']:
            # Manually simplify the column names.
            df.columns = ['Sports, Women, Scholarships Given',
                          'Sports, Women, Offered',
                          'Sports, Men, Scholarships Given',
                          'Sports, Men, Offered']
            s = pd.Series(index = df.columns)
            for col_name in df.columns:
                s[col_name] = df[col_name].dropna().index.tolist()
            page_s = page_s.append(s)
            
    # ADDITIONAL EXTRACTIONS
    ##########################################################################
    # Get school Name and Description, which are not in a table.
    if page.h1 and page.h1.text != EMPTY_H1:
        page_s['Name'] = page.h1.text
    if page.p:
        page_s['Description'] = page.p.text

    # Get the FAFSA code from the strangely formatted 2nd table of section10.
    div = page.find('div', id='section10')
    if div:
        tables = div.find_all('table')
        if len(tables) == 3:
            # The FAFSA code is the last six characters of this text.
            page_s['FAFSA Code'] = tables[2].tbody.th.text[-6:]

    # Get lists of majors / programs of study from strangely formatted tables.
    caption_strings = ['Undergraduate Majors',
                       "Master's Programs of Study",
                       'Doctoral Programs of Study']
    for caption_string in caption_strings:
        regex = re.compile(caption_string)
        caption = page.find('caption', string=regex)
        if caption:
            vals = []
            for tag_name in ['th','td']:
                tag = caption.find_next(tag_name)
                if tag:
                    tag_string = "---".join(tag.stripped_strings)
                    vals += tag_string.split('---')
            page_s[caption_string] = vals
            
    # Get values from tables with no label (but do have captions!).
    captions = ['Entrance Difficulty',
               "Master's Degrees Offered",
               "Doctoral Degrees Offered"]
    for caption in captions:
        regex = re.compile(caption)
        caption_tag = page.find('caption', string = regex)
        if caption_tag:
            val = caption_tag.parent.tbody.th.get_text(' ', strip = True)
            page_s[caption] = val
    
    return page_s


def drop_duplicates(s):
    """For each duplicate index in input pandas Series object 's', this
    function checks that duplicate index values are equal. If all duplicate
    index values are equal, duplicate entries in the Series are dropped."""
    s = s.dropna() # drop labels with null vals
    
    first_dups_mask = s.index.duplicated(keep = 'first')
    last_dups_mask = s.index.duplicated(keep = 'last')
    
    first_dups = s[first_dups_mask].sort_index()
    last_dups = s[last_dups_mask].sort_index()
    
    diff_dups = (first_dups != last_dups)
    
    msg = f"Some dup labels have diff vals.\n{diff_dups}"
    assert sum(diff_dups) == 0, msg
    
    s = s[~last_dups_mask] # drop last dups, keep first.
    
    return s


def main():
    
    schools = []
    exceptions = []
    
    for school_id in SCHOOL_IDS:

        # Hold scraped data for all six pages in pandas Series object.
        school_s = pd.Series()

        try:
            for page_id in PAGE_IDS:

                # Request and convert page into BeautifulSoup object.
                page = get_collegedata_page(school_id, page_id)

                # Relabel some HTML tag strings to prevent data loss to dups.
                page = relabel(page)

                # Extract data from page into a pandas Series object.
                page_s = extract(page)

                if not page_s.empty:
                    # Append extracted page Series to total school Series.
                    school_s = school_s.append(page_s)
                else:
                    break
                    
        except Exception:
            exceptions.append([school_id, Exception])
        else:
            # Drop duplicate entries if values are also duplicated.
            school_s = drop_duplicates(school_s)
            school_s.name = school_id
            schools.append(school_s)
        finally:
            clear_output(wait = True)

    return schools, exceptions