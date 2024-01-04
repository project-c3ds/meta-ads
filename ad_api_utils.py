import requests
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import csv

### MANUAL VARIABLES ###

with open('token.txt', 'r') as f:
    ACCESS_TOKEN = f.read()

# load the complete list of country codes from file
# COUNTRY_CODES_PATH = WORKING_DIR + 'ad_transparency_tools_country_codes.txt'
abs_dir = str(os.path.dirname(__file__)) + '/' # get folder this ad_api_utils.py file is in
COUNTRY_CODES_PATH = abs_dir + 'ad_transparency_tools_country_codes.txt'
with open(COUNTRY_CODES_PATH, 'r') as f:
    COUNTRY_CODES = f.read().split('\n')

# define the global default parameters and fields for searching
# see https://developers.facebook.com/docs/marketing-api/reference/ads_archive/ for reference
DEFAULT_PARAMS = {
    'ad_reached_countries': str(COUNTRY_CODES),
    'ad_active_status': 'ALL',
    'limit': '500',
    # 'search_type': 'KEYWORD_EXACT_PHRASE', # "will treat the words in search_terms as a single phrase, and only return results that match that exact phrase. To search for multiple phrases at once, separate groups of words in search_terms by commas. This will retrieve results that contain an exact match for every phrase."
    'unmask_removed_content': 'true',
    'ad_type': 'POLITICAL_AND_ISSUE_ADS'
}

# ad_type: {ALL, `C`REDIT_ADS, EMPLOYMENT_ADS, HOUSING_ADS, POLITICAL_AND_ISSUE_ADS}

# define all the fields to be returned by ad library search
# by default this is all possible fields
# see https://developers.facebook.com/docs/marketing-api/reference/archived-ad/ for full field descriptions
DEFAULT_FIELDS = ['id', 'ad_creation_time',
                  
                  # universal fields
                  'ad_snapshot_url', 'languages', 'page_id', 'page_name', 'publisher_platforms', 
                  'ad_delivery_start_time', 'ad_delivery_stop_time', # times in UTC as string

                  # ad text content
                  # in each unique ad card...
                  'ad_creative_bodies', # ... text which displays in each unique ad card
                  'ad_creative_link_captions', # ... captions in each call to action section
                  'ad_creative_link_descriptions', # ... descriptions in each call to action section 
                  'ad_creative_link_titles', # ... titles in each call to action section
                  
                  # EU only
                  'age_country_gender_reach_breakdown', 'beneficiary_payers',
                  'eu_total_reach',
                  'target_ages', 'target_gender', 'target_locations',

                  # political and issue ads only
                  'spend', 'bylines', 'currency',
                  'delivery_by_region', 'demographic_distribution', 
                  'estimated_audience_size', 'impressions'
                  ]


### FUNCTIONS ###

def get_json_response(url, access_token, n_tries=3):
    '''
    get a single API response as a json object
    occasionally a request will fail. mitigate this by retrying up to 3 times by default
    '''
    headers = {"Authorization": "Bearer {}".format(access_token)}

    for i in range(n_tries): # tries request up to max n_tries
        if i > 0:
            print(f'retrying ({i+1}/{n_tries})', end="\r")
        response = requests.request("GET", url, headers=headers)
        if response.status_code == 200: # if response is good
            return response.json() # return good response
    
    print(f'request failed {n_tries} times')
    raise Exception(response.status_code, response.text) # raise Exception if bad response returned n_tries times

def make_url(params, fields):
    '''
    make API query URL based on given search parameters, returning specified fields (including ad id by default)
    
    params: dict of parameter_name,parameter_value pairs
        see      for reference
    fields: list of fields as strings
        # see https://developers.facebook.com/docs/marketing-api/reference/archived-ad/ for reference
    '''
    base = 'https://graph.facebook.com/v11.0/ads_archive?'
    params_str = '&'.join(['='.join(x) for x in zip(params.keys(), [str(val) for val in params.values()])])
    
    #ad id required field for indexing
    if 'id' not in fields:
        fields.append('id')
    
    fields_str = '&fields=' + str(fields)
    
    return base + params_str + fields_str

def get_response_df(url, access_token=ACCESS_TOKEN):
    '''
    chain together multi-page API responses and return all data as single dataframe
    '''
    response = get_json_response(url, access_token) # get the first page of results
    data = response['data'] # collect the data 

    ads_df = pd.DataFrame() # initialize empty dataframe
    
    n_responses = 0
    while len(data) > 0: # until the most recently returned page of data is empty
        n_responses += 1 # increment response count
        print(f'page {n_responses}', end="\r") # print running page/response total

        data = pd.DataFrame(data).set_index('id') # transform data to a dataframe and make id index
        ads_df = pd.concat([ads_df, data], axis=0, join='outer') # add data to previously loaded pages
        url = response['paging']['next'] # get url for next page
        
        response = get_json_response(url, access_token) # get response for next page
        data = response['data'] # get data from response

    return ads_df

# doing the scrape

from itertools import zip_longest
def get_chunks(iterable, n):
    args = [iter(iterable)] * n
    return [[l for l in x if not l is None] for x in zip_longest(*args)]

def search(custom_params, custom_fields, default_params=DEFAULT_PARAMS, default_fields=DEFAULT_FIELDS):
    '''
    wrapper function: called by user to perform search
    specify search terms or page ids in custom parameters variable
    '''
    # set the default search parameters and fields
    params = default_params
    fields = default_fields

    # custom params includes search terms and dates
    # can also include variation to the other default parameters (e.g. ad reached countries)
    for param, val in custom_params.items():
            params[param] = val
    
    # if custom fields are specified, use those instead of the default fields
    if not custom_fields is None:
        fields = custom_fields

    # nothing is returned from this block if a) there are no actors specified, or b) fewer than 10 actors are specified
    if params.get('search_page_ids') is not None: # if actor ids have been specified
        actor_ids = params['search_page_ids'].strip(('][')).replace("'", '').split(', ') # get list of string ids
        if len(actor_ids) > 10: # if more than 10 actors are specified
            actor_groups = get_chunks(actor_ids, 10) # chunk the list into groups of at most 10
            dfs = []
            for ids in actor_groups: # for each group of ids
                params['search_page_ids'] = str(ids) # set the search parameter for that group
                url = make_url(params, fields) # make the url for this group
                ads_df = get_response_df(url) # search for this group of ids
                dfs.append(ads_df) # add the response to the running collection of dfs
            ads_df = pd.concat(dfs) # combine results from all groups of ids together
            params['search_page_ids'] = str(actor_groups) # add all the actor ids back to the parameters but leave them in their groups (for documentation purposes)
            return ads_df, params # return the results and parameters used

    # combine params and fields into API search url
    url = make_url(params, fields)
    ads_df = get_response_df(url)

    return ads_df, params

from pathlib import Path
from datetime import datetime, timezone
import json
import os
def save_search_results_and_log(df, params, save_folder, save_fname):
    '''
    given search parameters used and data returned, save data along with log (of parameters and search time)
    save with custom filename; if this filename exists already, add numeric filename suffix
    '''
    Path(save_folder).mkdir(parents=True, exist_ok=True) # check save directory exists. if it doesn't, create it. if it does, ignore.

    # check save folder is correct format with '/'
    if not save_folder.endswith('/'):
        save_folder = save_folder + '/'

    # check for duplicate file names
    matches = [os.path.splitext(f)[0] for f in os.listdir(save_folder) if f.startswith(save_fname)] # excludes file extension of every match
    matches = [f for f in matches if not f.endswith('_log')] # remove log files from match list
    if len(matches) == 1:
        # only one match - add 1 to fname (i.e. first duplicate)
        save_fname = save_fname + '_' + '1'
    elif len(matches) > 1:
        # more than one match - 'fname_1' must already exist
        # the length of the matches list is the next ind: [f, f_1, f_2] --> f_3 is next
        save_fname = save_fname + '_' + str(len(matches))

    # save scraped data
    df.to_pickle(f'{save_folder}{save_fname}.pkl') # save dataframe as pickle

    # save log
    save_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S:%f') # get current time (to the microsecond) as string
    params['save_time_UTC'] = save_time # add save time as parameter for log

    with open(f'{save_folder}{save_fname}_log.json', 'w', encoding='utf-8') as f:
        json.dump(params, f, ensure_ascii=False, indent=4)