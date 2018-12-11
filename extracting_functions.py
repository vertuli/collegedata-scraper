import pandas as pd
import re
import bs4
from scrapecollegedata import config

# Get config values.
#with open('config.json', 'r') as f:
#    config = json.load(f)

def extract_tables(soup):
    s = pd.Series()
    # Convert all HTML tables in page to a list of pandas DataFrames.
    df_list = pd.read_html(soup.decode(), na_values = config['NA_VALS'], index_col = 0)

    # Split dfs into separate lists depending on dimension.
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
                label = 'Factor, ' + row_name
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
        col_level_names = ['Sport', 'Offered']
        if df.columns.names == ['Sport', 'Offered']:
            # Manually simplify the column names.
            df.columns = ['Sports, Women, Scholarships Given',
                          'Sports, Women, Offered',
                          'Sports, Men, Scholarships Given',
                          'Sports, Men, Offered']
            table_s = pd.Series(index = df.columns)
            for col_name in df.columns:
                vals = df[col_name].dropna().index.tolist()
                if vals:
                    table_s[col_name] = vals
            s = s.append(table_s)
    return s

# ADDITIONAL EXTRACTIONS
##########################################################################

def get_non_table_vals(soup):
    # Get school Name and Description, which are not in a table.
    s = pd.Series()
    s['Name'] = soup.h1.text
    if soup.p:
        s['Description'] = soup.p.text
    return s


#def get_fafsa(soup):
#    # Get the FAFSA code is stuck in a <th> tag, for some reason.
#    s = pd.Series()
#    th_tag = soup.find('th', string = 'FAFSA')
#    if th_tag:
#        # The FAFSA code is the last six characters of this text.
#        s['FAFSA Code'] = th_tag.text
#    return s
#


def get_majors(soup):
    # Get lists of majors / programs of study from strangely formatted tables.
    s = pd.Series()
    caption_strings = ['Undergraduate Majors',
                       "Master's Programs of Study",
                       'Doctoral Programs of Study']
    for caption_string in caption_strings:
        regex = re.compile(caption_string)
        caption = soup.find('caption', string=regex)
        if caption:
            vals = []
            for tag_name in ['th','td']:
                tag = caption.find_next(tag_name)
                if tag:
                    tag_string = "---".join(tag.stripped_strings)
                    vals += tag_string.split('---')
            s[caption_string] = vals
    return s


def get_non_labeled_vals(soup):
    # Get values from tables with no label (but do have captions!).
    s = pd.Series()
    captions = ['Entrance Difficulty',
               "Master's Degrees Offered",
               "Doctoral Degrees Offered"]
    for caption in captions:
        regex = re.compile(caption)
        caption_tag = soup.find('caption', string = regex)
        if caption_tag:
            val = caption_tag.parent.tbody.th.get_text(' ', strip = True)
            s[caption] = val

    return s