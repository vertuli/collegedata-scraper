import json
import sys
import logging
import pandas as pd

import collegedatascraper.reformatters
import collegedatascraper.extractors


# Get config values.
with open('config.json', 'r') as f:
    config = json.load(f)

# Setup logging.
log_path = config['PATHS']['ERROR_LOG']
logging.basicConfig(filename=log_path, filemode='w', level=logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_single_school(school_id, silent=False):
    """Get six pages of data associated with a CollegeData.com school_id and
    return a pandas Series object holding extracted values.
    """
    try:
        # Get DataFrames for the <table> on all six pages for the school_id.
        df_list = []
        for page_id in range(1, 7):
            df_list += collegedatascraper.extractors.get_df_list(
                school_id,
                page_id
            )

        # Separate dataframes with single <td> from those with multiple <td>.
        singlecol_df_list = []
        table_df_list = []
        for df in df_list:
            if len(df.columns) == 1:
                singlecol_df_list.append(df)
            if len(df.columns) > 1:
                table_df_list.append(df)

        # Extract a Series from the single col DataFrames.
        singlecol_df = pd.concat(singlecol_df_list, axis=0, sort=False)
        singlecol_s = singlecol_df.iloc[:, 0]

        # Extract a Series from the table DataFrames.
        tables_s = collegedatascraper.extractors.df_to_series(table_df_list)

        # Merge both Series into one, and sort the index.
        merged_s = pd.concat([singlecol_s, tables_s])
        merged_s.sort_index(inplace=True)

        # Drop duplicate indices and their vals and name the Series.
        s = merged_s[~merged_s.index.duplicated()]
        s.name = school_id

    except IOError:
        s = None
        msg = f'Failed while processing school {school_id}.'
        logging.warning(msg)
    except Exception as e:
        s = None
        msg = f'Exception encountered while getting school {school_id}!\n{e}'
        logging.critical(msg, exc_info=True)
    else:
        msg = f'Successfully scraped school {school_id}.'
    finally:
        if not silent:
            print(msg)
    return s


def get_school(start_id, end_id=None, silent=False):
    """Runs get_school for every school_id in range from start_id to end_id,
    returning a pandas DataFrame. Default range is from 1 to 5000."""
    if not end_id:
        end_id = start_id

    all_s_list = []
    try:
        for school_id in range(start_id, end_id + 1):
            s = get_single_school(school_id, silent=silent)
            all_s_list.append(s)

        # Remove None values from the Series list, if any.
        s_list = [s for s in all_s_list if s is not None]

    except KeyboardInterrupt:
        msg = 'Stopped!'
    except Exception as e:
        msg = f'Exception occured after getting school(s)!\n{e}'
        logging.critical(msg, exc_info=True)
    else:
        msg = 'Successfully finished!'
    finally:
        output = build_output(s_list)
    return output


def build_output(s_list):
    """Construct appropriate output from list of pandas Series."""
    if s_list:
        df = pd.DataFrame(s_list)
        df.index = df.index.rename('School ID')
        if len(df) > 1:
            output = df  # Output a DataFrame.
        if len(df) == 1:
            output = df.iloc[0]  # Output a Series.
    else:
        output = None

    return output


def get_input(args):
    """Get start and end school IDs from user, or else from config file."""
    try:
        if len(args) > 1 and args[1] > 1:
            start_id = int(args[1])
            if len(args) > 2 and args[2] > start_id:
                end_id = int(args[2])
        else:
            start_id = config['SCHOOL_ID']['START']
            end_id = config['SCHOOL_ID']['END']
    except ValueError:
        msg = 'Range start and end must be positive integers.'
        logging.warning(msg, exc_info=True)
        raise

    return start_id, end_id


def main():
    """This function executes if module is run as a script."""
    start_id, end_id = get_input(sys.argv)

    csv_path = config['PATHS']['CSV']
    silent = config['SILENT']

    # Get data for each school and export to .csv file.
    df = get_school(start_id, end_id, silent=False)
    if df and not df.empty:
        df.to_csv(csv_path, index_label='School ID')
        msg = f'Scraped {len(df)} schools to {csv_path}.'
    else:
        msg = f'No schools scraped.'
    if not silent:
        print(msg)


if __name__ == '__main__':
    main()
