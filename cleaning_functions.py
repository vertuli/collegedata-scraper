import re

def strip_tag_contents(soup):
    # Strip all HTML from <th>, <td>, and <caption> tags, leaving only text.
    for tag in soup.find_all(['th', 'td', 'caption']):
        tag.string = tag.get_text(' ', strip = True)
    return soup

def add_sub_labels(soup):
    # Prepend parent labels to the <th> row label tags having class = 'sub'.
    for tag in soup.find_all('th', class_ = 'sub'):
        tag_text = tag.get_text(' ', strip = True)
        parent_tag = tag.find_previous('th', class_ = None)
        parent_text = parent_tag.get_text(' ', strip = True)
        tag.string = parent_text + ', ' + tag_text
    return soup


def add_indent_labels(soup):
    # Do the same for tags without class = 'sub' but with tab indents '\xa0':
    regex = re.compile('\xa0')
    for tag in soup.find_all('th', string = regex):
        tag.string = tag.get_text(' ', strip = True)
        header_tag = None
        if tag.string == 'Women':
            header_tag = tag.parent.find_previous('tr').th
        if tag.string == 'Men':
            header_tag = tag.parent.find_previous('tr').find_previous('tr').th
        if header_tag:
            tag.string = header_tag.string + ', ' + tag.string
    return soup


def add_gpa_labels(soup):
    # Prepend labels to GPA row labels.
    regex = re.compile('Grade Point Average')
    caption = soup.find('caption', string = regex)
    if caption:
        gpa_table = caption.parent
        header_tag = gpa_table.tbody.th
        header_tag.string = 'GPA, Average'
        sub_tags = gpa_table.find_all('th')[1:]
        for tag in sub_tags:
            tag.string = header_tag.string + ', ' + tag.string
    return soup


def add_finaid_prefixes(soup):
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


def restructure_finaid_forms(soup):
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
    return soup


def replace_hyperlinks(soup):
    # Replace table data cells with links with the link address itself.
    td_tags = soup.find_all('td')
    for tag in td_tags:
        link_tag = tag.find('a')
        if link_tag:
            tag.string = link_tag['href']
    return soup


def label_emails_websites(soup):
    # Prepend labels to duplicate E-mail and Web Site labels.
    regex = re.compile('Financial Aid Office')
    caption = soup.find('caption', string = regex)
    if caption:
        email_tag = caption.find_next('th', string = 'E-mail')
        email_tag.string = 'Financial Aid Office E-mail'
        website_tag = caption.find_next('th', string = 'Web Site')
        website_tag.string = 'Financial Aid Office Web Site'
    return soup


def fix_population_label(soup):
    # Fix city Population labels (varying label contains city name).
    regex = re.compile('Population')
    th_tag = soup.find('th', string = regex)
    if th_tag:
        th_tag.string = "City Population"
    return soup


def fix_entrance_difficulty(soup):
    # Rename the duplicate Entrance Difficulty label on the Overview page.
    div = soup.find('div', id = 'section0')
    if div:
        th_tag = div.find('th', string = 'Entrance Difficulty')
        th_tag.string = 'Entrance Difficulty, Category'
    return soup


def prepend_other_app_reqs(soup):
    # Prepend labels to 'Other Application Requirements' table.
    caption = 'Other Application Requirements'
    caption_tag = soup.find('caption', string = caption)
    if caption_tag:
        th_tags = caption_tag.parent.find_all('th')
        for tag in th_tags:
            text = tag.get_text(' ', strip = True)
            tag.string = 'Application Requirement, ' + text
    return soup


def prepend_security(soup):
    # Prepend labels to 'Security' table.
    div = soup.find('div', id = 'section22')
    if div:
        th_tags = div.find_all('th')
        for tag in th_tags:
            text = tag.get_text(' ', strip = True)
            tag.string = 'Security, ' + text
    return soup


def delete_map_widget(soup):
    # Delete the row containing the map widget.
    b_tag = soup.find('b', string = 'View Larger Map')
    if b_tag:
        parent_row = b_tag.find_parent('tr')
        parent_row.decompose()
    return soup