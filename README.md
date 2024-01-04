# Scraping ads - which files?
* `ad_search_template.py` is a generic file - a customised version of this is the basis for an ad scrape
* To scrape ads with certain keywords and/or from certain actors, copy `ad_search_template.py`, fill in these relevant details and run the file.
* This lightweight `ad_search.py` file points to a utils file `ad_api_utils.py` containing all the python functions that actually carry out the scrape. 
* The ad search file can be in a different directory from this repo, as long as the variable `UTILS_FOLDER_PATH` correctly points to the parent folder of the `ad_api_utils.py` file (i.e., this repo). 

# Customising search parameters & fields
* The full list of search parameters that can be used with the Meta Ads API is found at https://developers.facebook.com/docs/graph-api/reference/ads_archive/
* The only parameter absolutely required by the API is `ad_reached_countries`. In practice, to avoid returning too many ads, one of at least `search_terms`, `search_page_ids`, `ad_delivery_date_min`, and `ad_delivery_date_max` should be used. These have generic default values as placeholders in the `ad_search_template.py` file.
* Other custom parameters can be specified by adding entries to the `custom_params` dict. These may include regions, languages, platforms, or string search types.
* Some parameters have default values included in the `ad_api_utils.py` file itself - these are sensible defaults for most purposes, and it is not recommended that these are changed. However, if changing them is required (e.g. if you are searching for only currently active ads), any values specified in the `ad_search` file will take precedence (i.e. wil overwrite the `ad_api_utils` defaults).
* By default, all fields are returned in each search; a full list of these is found at https://developers.facebook.com/docs/marketing-api/reference/archived-ad/
* To customise fields, simply specify a list of `custom_fields` in the `ad_search` file.

# Saving data
* Once the customised `ad_search_template.py` file is run, the ad data (in the form of a pickled pandas dataframe) and a log file (.txt) will be saved to `SAVE_FOLDER` you have specified (by default, simply `/data/` in whichever directory the `ad_search` file is in).
* This log file contains details of the parameters used for the search, as well as the time the search was run.
* Running the search file again (with the same save name - `SAVE_FNAME`) will not over-write the first set of data; further scrapes will be saved with incrementing numbers appended (e.g. scrape_2.pkl, scrape_3.pkl, etc.)
* It is recommended that one folder is used to store just the raw scrapes (and their logs), and any data processing is done in another directory. This avoids issues with the incrementing file naming.

# Processing &/ cleaning data
* The "raw" data obtained from the API contains some fields that require processing before being easy to use. For example, spend is returned as a dictionary: `{'lower_bound': X, 'upper_bound': Y}`.
* To process the data into a useable form, import the `preproc` function from the `processing_utils.py` file in the repo and run it on the raw dataframe.
* This file:
    * converts datetime columns to datetime,
    * splits range fields into two columns,
    * converts spend columns into USD (historical rates at the time of ad delivery start, falling back on current rates)
    * calculates the minimum possible spend based on the ads duration (0.5 or 1 USD per day, depending on currency used)
    * calculates a lower bound for the spend. This is the highest of the API-returned spend lower (often 0) and the minimum possible spend based on duration. This is to provide a meaningful lower spend value, avoiding summed 0s (for high-freq, low-spend ad campaigns).
* Other useful processing functions are included:
    * `get_daily_active_matrix`: returns a boolean dataframe with ad_id index and date columns - True if that ad is active on that date.
    * `get_daily_spend_matrix`: equivalent to the above but instead lists the ad's amortized (i.e. averaged over its active lifetime) spend for that date.
    * `get_regional_impressions`: get a dataframe of ad impressions by region (sub-country regions in most cases)
    * `get_country_impressions`: aggregates the above regions into countries. region identification was part-automated (using geolocating libraries) and part manual (based on co-occurring regions with impressions, and lack of certain countries in dataset entirely). NB: these caveats mean this data should be framed as an estimate and quoted to perhaps 2 or 3 s.f.
