import bs4
import re

##############################################################################
# GENERAL CLEANING
##############################################################################
def clean(soup, page_id):
    """Apply general cleaning functions to the soup object, then specific
    cleaning functions depending on page_id.
    """
    # Clean <caption> strings.
    tags = soup.find_all('caption')
    for tag in tags:
        tag.string = tag.get_text(' ', strip = True)

    # Clean <td> tag strings. 
    # Replace <td> tag strings with URL, if <a> link tag inside <td> tag.
    # Replace any other HTML in tags with '---', if it exists.
    tags = soup.find_all('td')
    for tag in tags:
        a_tag = tag.find('a')
        if a_tag:
            tag.string = a_tag['href']
        else:
            tag.string = tag.get_text('---', strip = True)

    # Restructures anomalous tables that are using their <caption> string as 
    # a 'label' and storing actual data in both <th> and <td> tags.
    bad_table_captions = [
        'Undergraduate Majors',
        "Master's Programs of Study",
        'Doctoral Programs of Study',
        "Master's Degrees Offered",
        'Doctoral Degrees Offered',
        'Entrance Difficulty'
    ]
    caption_tags = [tag for tag in soup.find_all('caption') 
                    if tag.string in bad_table_captions]
    for caption_tag in caption_tags:
        tbody_tag = caption_tag.find_next('tbody')
        tbody_string = '---'.join(tbody_tag.stripped_strings)
        tbody_tag.clear()
        tbody_tag = insert_row(
            parent_tag = tbody_tag,
            label = caption_tag.string,
            val = tbody_string
        )

    # Clean <th> strings.
    for tag in soup.find_all('th'):
        tag.string = tag.get_text(' ', strip = True)
        # Prefix parents to the <th> row label tags with class = 'sub'.
        prefix = None 
        if tag.get('class') == ['sub']:
            prefix = tag.find_previous('th', class_ = None).string
            tag.string = prefix + ', ' + tag.string

    # Fix duplicate gender breakdown labels that occur under these labels:
    labels = [
    'Undergraduate Students',
    'Overall Admission Rate', 
    'Students Enrolled',
    'All Undergraduates'
    ]
    th_tags = [tag for tag in soup.find_all('th') if tag.string in labels]
    for th_tag in th_tags:
        first_th_tag = th_tag.find_next('th')
        if first_th_tag.string == 'Women':
            first_th_tag.string = th_tag.string + ', Women'
            second_th_tag = first_th_tag.find_next('th')
            if second_th_tag.string == 'Men':
                second_th_tag.string = th_tag.string + ', Men'

    # More specific cleaning:
    if page_id == 1:
        soup = clean_page1(soup)
    if page_id == 2:
        soup = clean_page2(soup)
    if page_id == 3:
        soup = clean_page3(soup)
    if page_id == 4:
        soup = clean_page4(soup)
    if page_id == 5:
        soup = clean_page5(soup)
    if page_id == 6:
        soup = clean_page6(soup)

    return soup

##############################################################################
# UTILITY FUNCTION
##############################################################################
def insert_row(parent_tag, label = None, val = None):
    """Insert <tr> w/<th> for label and a <td> for val into parent_tag."""
    soup = bs4.BeautifulSoup(markup = '', features = 'lxml')
    th_tag = soup.new_tag('th')
    th_tag.string = label
    tr_tag = soup.new_tag('tr')
    tr_tag.insert(0, th_tag)
    td_tag = soup.new_tag('td')
    td_tag.string = val
    tr_tag.insert(1, td_tag)
    parent_tag.insert(0, tr_tag)
    return parent_tag

##############################################################################
# CLEANING SPECIFIC PAGES
##############################################################################
def clean_page1(soup):
    """Additional cleaning for page 1"""
    # Add school Name, found only in the <h1> string, to the first <tbody>.
    tbody_tag = soup.find('tbody')
    tbody_tag = insert_row(tbody_tag, label = 'Name', val = soup.h1.text)

    # Similarly, add the Description, found only in a <p> tag outside a table.
    p = soup.find('p')
    if p:
        tbody_tag = insert_row(tbody_tag, label = 'Description', val = p.text)

    # Delete shortened 'Selection of Students' table - full version on page 2.
    caption = 'Selection of Students'
    caption_tag = soup.find('caption', string = caption)
    if caption_tag:
        table_tag = caption_tag.find_parent('table')
        table_tag.decompose()

    # Delete the useless row containing the map widget.
    th_tag = soup.find('th', string = re.compile('View Larger Map'))
    if th_tag:
        tr_tag = th_tag.find_parent('tr')
        tr_tag.decompose()

    # Fix city Population labels (varying label contains city name).
    regex = re.compile('Population')
    th_tag = soup.find('th', string = regex)
    if th_tag:
        th_tag.string = 'City Population'

    # Rename the GPA tag to line up with an identical value on another page.
    th_tag = soup.find('th', string = 'Average GPA')
    if th_tag:
        th_tag.string = 'GPA, Average'

    return soup


def clean_page2(soup):
    """Additional cleaning for page 2"""
    # Rename the duplicate Entrance Difficulty label on the Overview page.
    th_tag = soup.find('th', string = 'Entrance Difficulty')
    if th_tag:
        th_tag.string = 'Entrance Difficulty, Description'

    # Add missing column label to first column of 'Examinations' table.
    caption = 'Examinations'
    caption_tag = soup.find('caption', string = caption)
    if caption_tag:
        thead_tag = caption_tag.find_next('thead')
        thead_tag.td.string = 'Requirement'

    # Prepend labels to GPA row labels.
    regex = re.compile('Grade Point Average')
    caption_tag = soup.find('caption', string = regex)
    if caption_tag:
        gpa_table = caption_tag.parent
        header_tag = gpa_table.tbody.th
        header_tag.string = 'GPA, Average'
        sub_tags = gpa_table.find_all('th')[1:]
        for tag in sub_tags:
            tag.string = 'GPA, ' + tag.string

    # Prepend labels to 'Other Application Requirements' table.
    caption = 'Other Application Requirements'
    caption_tag = soup.find('caption', string = caption)
    if caption_tag:
        th_tags = caption_tag.parent.find_all('th')
        for tag in th_tags:
            text = tag.get_text(' ', strip = True)
            tag.string = 'Application Requirements, ' + text

    return soup


def clean_page3(soup):
    """Additional cleaning for page 3"""
    # Prepend labels to duplicate E-mail and Web Site labels.
    caption = soup.find('caption', string = 'Financial Aid Office')
    if caption:
        email_tag = caption.find_next('th', string = 'E-mail')
        email_tag.string = 'Financial Aid Office, E-mail'
        website_tag = caption.find_next('th', string = 'Web Site')
        website_tag.string = 'Financial Aid Office, Web Site'

    # Restructure the strange Forms Required / Cost to File table.
    th_tag = soup.find('th', string = "Forms Required")
    if th_tag:
        tbody_tag = th_tag.find_next('tbody')
        for th in tbody_tag.find_all('th'):
            if 'FAFSA' in th.text:
                fafsa_code = th.text[-6:]
                th.string = 'FAFSA Code'
                td = th.find_next('td')
                if td:
                    td.string = fafsa_code

    # Prepend labels to financial aid information
    div = soup.find('div', id = 'section11')
    if div:
        for table in div.find_all('table')[0:2]:
            caption_string = table.caption.get_text(' ', strip = True)
            th_tags = table.find_all('th')
            for tag in th_tags:
                string = caption_string + ', '
                string = string + tag.get_text(' ', strip = True)
                tag.string = string
    return soup


def clean_page4(soup):
    """Additional cleaning for page 4"""
    # Add prefixes to Curriculum Requirements.
    div_tag = soup.find('div', id = 'section14')
    if div_tag:
        table_tag = div_tag.find('table')
        if table_tag:
            th_tags = table_tag.find_all('th')
            for th_tag in th_tags:
                th_tag.string = 'Curriculum Requirements, ' + th_tag.string
    return soup


def clean_page5(soup):
    """Additional cleaning for page 5"""
    # Fix city Population labels (varying label contains city name).
    regex = re.compile('Population')
    th_tag = soup.find('th', string = regex)
    if th_tag:
        th_tag.string = "City Population"

    # Fix the header on the sports table.
    caption = "Intercollegiate Sports Offered"
    caption_tag = soup.find('caption', string = caption)
    if caption_tag:
        thead_tag = caption_tag.find_next('thead')
        if thead_tag:
            # Clear <thead> and add to it a new <tr> tag, with labeled <th>.
            thead_tag.clear()
            tr_tag = soup.new_tag('tr')
            thead_tag.insert(0, tr_tag)
            th_tag = soup.new_tag('th')
            th_tag.string = caption
            tr_tag.insert(0, th_tag)
            # Add new <td> tags holding column labels as strings to <tr>.
            col_labels = [
                'Women', 'Women, Scholarships Given', 
                'Men', 'Men, Scholarships Given'
            ]
            for i, col_label in enumerate(col_labels):
                td_tag = soup.new_tag('td')
                td_tag.string = col_label
                tr_tag.insert(i + 1, td_tag)

    return soup


def clean_page6(soup):
    """Additional cleaning for page 6"""
    # No additional cleaning needed.
    return soup