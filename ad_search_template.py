# this file designed to be as lightweight as possible for easy alteration for different searches
# most defaults and code is found in ad_api_utils, including default parameters and fields
# for a new search, copy this file to a new destination folder, alter parameters accordingly, and run from terminal

# locate the utils file and import functions
UTILS_FOLDER_PATH = '.../meta_ads/'
import sys
sys.path.append(UTILS_FOLDER_PATH)
from ad_api_utils import *

# these are some commonly-used parameters for searching. full list at https://developers.facebook.com/docs/graph-api/reference/ads_archive/
custom_params = {
    'search_terms': str(['a', 'b', 'c']),
    'ad_delivery_date_min': '2021-01-01',
    'ad_delivery_date_max': '2021-01-01',
}

# optionally load in actor ids from txt file with each id on a different line
ACTOR_IDS_FPATH = None
if not ACTOR_IDS_FPATH is None:
    with open(ACTOR_IDS_FPATH, 'r') as f:
        actor_ids = f.read().splitlines()
    custom_params['search_page_ids'] = str(actor_ids)

# specify search fields
# None --> get all fields
# subset of fields specified in list --> get only those fields
custom_fields = None

SAVE_FOLDER = 'data'
SAVE_FNAME = 'ad_search' # don't include file extension in this filename string

df, params = search(custom_params, custom_fields)
save_search_results_and_log(df, params, SAVE_FOLDER, SAVE_FNAME)