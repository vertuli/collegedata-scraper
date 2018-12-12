# collegedata-scraper

Running `collegedata_scraper.py` with default configuration will request from CollegeData.com up to six different pages of information associated with each school with `schoolId` from 1 to 5000, scraping up to nearly 300 fields of data for each school into one row in `collegedata.csv` while logging to `errors.log`.


## Requirements

This script depends on the `bs4` and `pandas` packages, as well as the functions in the included `cleaning_functions.py` module.

## Details

Each school has a `schoolId` and six associated pages of information:
1. Overview
2. Admission
3. Money Matters
4. Academics
5. Campus Life
6. Students

URLs are in this form:
https://www.collegedata.com/cs/data/college/college_pg02_tmpl.jhtml?schoolId=59
The `schoolId=59` is Penn State; the `pg02` is the "Admission" information page.

Not every `schoolId` is associated with an actual school. If any page associated with such a `schoolId` is requested, CollegeData.com returns a page with the title `"Retrieve a Saved Search"`, which the scraper identifies and skips further page requests and tries the next `schoolId` in the list.

The list of `schoolId` to scrape can be modified in two ways:
- Editing the start and end values in the `config.json` file.
- If running from the command line, supplying arguments in the form `collegedata.py <start ID> <stop ID>`.

On my last run, I scraped up to 273 fields from 2029 schools in about 4 hours (most schools have `schoolId` below 3000).

## Output

Most fields are scraped 'as is' into the CSV, with labels and values as provided (or directly derived) from the page in a nearly unmodified state. Many of these fields are strings that contain multiple discrete pieces of numeric or categorical information which require further wrangling into separate columns of appropriate type with `pandas` for further analysis.