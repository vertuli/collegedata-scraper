# collegedata-scraper


Returns a pandas DataFrame of school information extracted from the website CollegeData.com, with each row corresponding to a successfully scraped schoolId in the range [start, stop], inclusive, with each column corresponding to labeled information fields on the website.

## Notes
CAUTION: Without any start or end parameters provided, will use the default parameters provided in config.json, which could scrape thousands of schoolIds and take hours.

'scrape' logs errors to a file located at a path defined in config.json.

## Usage
Getting a DataFrame of college data from a single schoolId:

```
>>> df = collegedatascraper.scrape(59)
Successfully scraped school 59.

>>> df.info()
Successfully scraped school 59.
<class 'pandas.core.frame.DataFrame'>
Int64Index: 1 entries, 59 to 59
Columns: 290 entries, 2016 Graduates Who Took Out Loans to Work-Study ...
dtypes: float64(67), object(223)
memory usage: 2.3+ KB
```

Getting a DataFrame of college data from a range of schoolIds:
```
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
```





Running `collegedata_scraper.py` with default configuration will request from CollegeData.com up to six different pages of information associated with each school with `schoolId` from 1 to 5000, scraping up to nearly 300 fields of data for each school into one row of the returned pandas DataFrame.

## CollegeData.com details

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

On my last run, I scraped just over 2000 schools in about 4 hours (most schools have `schoolId` below 3000, but I set the default end to 5000 just to be sure).