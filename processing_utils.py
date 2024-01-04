import pandas as pd
import numpy as np
from dateutil.parser import parse as parse_date
from currency_converter import CurrencyConverter
from datetime import datetime, timedelta

from sklearn.feature_extraction.text import CountVectorizer


### preprocessing ad dataframes - run functions in order of definition

def make_datetime(df, fields=['ad_creation_time', 'ad_delivery_start_time', 'ad_delivery_stop_time']):
    '''
    transform specified fields to datetime
    '''
    for field in fields:
        if field in df.columns:
            df[field] = pd.to_datetime(df[field])
    return df

def split_range_fields(df, fields=['spend', 'estimated_audience_size', 'impressions']):
    '''split range fields (interpreted by pandas as dictionaries) into separate lower and upper bound columns'''
    df = df.copy()
    for field in fields:
        if field in df.columns:
            # split spend into spend_lower and spend_upper
            # where values are missing, recorded in dataframe as nan (float) - if statement in list comprehension handles
            # this works as values are by default strings (?)
            df[f'{field}_lower'] = [float(x['lower_bound']) if not isinstance(x, float) else np.nan for x in df[field]]
            df[f'{field}_upper'] = [float(x.get('upper_bound', np.nan)) if not isinstance(x, float) else np.nan for x in df[field]]
            df.drop(columns=field, inplace=True)
    return df

def convert_single_value(value, currency, convertor, date, target_currency='USD'):
    if currency in convertor.currencies:
        value_USD = convertor.convert(value, currency, target_currency, date=date)
    else:
        value_USD = np.nan
    return value_USD

def convert_spend_cols(df, spend_cols=['spend_lower', 'spend_upper'], date_col='ad_delivery_start_time', currency_col='currency', target_currency='USD'):
    df = df.copy()

    # initialize converter object
    c = CurrencyConverter(fallback_on_missing_rate=True,
                          fallback_on_missing_rate_method='last_known',
                          fallback_on_wrong_date=True)
    
    for col in spend_cols:
        new_col = col + '_USD'
        df[new_col] = df.apply(lambda x: np.around(convert_single_value(x[col], x[currency_col], c, x[date_col], target_currency='USD'), 2), axis=1)
    return df

<<<<<<< HEAD
def calculate_duration(df, scrape_date=None):
    '''
    optionally fill active ads' end date with specified date of scrape (string)
    '''
=======

# less relevant for live analysis
# def get_min_spend_by_duration(duration, currency):
#     '''This function calculates the minimum possible spend for an ad, based on its duration and native currency.'''
#     # Facebook requires a minimum spend per day for each ad (in USD)
#     # This minimum value is 1 USD for the currencies listed, and 0.5 USD for all others
#     # https://developers.facebook.com/community/threads/812996445800356/
#     # https://developers.facebook.com/docs/marketing-api/reference/ad-campaign#create-considerations
#     limit_1usd = ['USD', 'AUD', 'CAD', 'SGD', 'JPY', 'NZD', 'TWD', 'EUR', 'CHF', 'SEK', 'HKD', 'GBP', 'ILS', 'NOK', 'KRW', 'DKK']
    
#     if isinstance(duration, timedelta):
#         duration = duration.days

#     if currency in limit_1usd:
#         return duration
#     else:
#         return duration / 2

def calculate_duration(df):
>>>>>>> parent of 3ce9137 (preprocessing updates)
    df = df.copy()
    df['duration'] = (df.ad_delivery_stop_time - df.ad_delivery_start_time).apply(lambda x: x.days) + 1
    return df

def get_min_spend_by_duration(df):
    '''This function calculates the minimum possible spend for an ad, based on its duration and native currency.'''
    # Facebook requires a minimum spend per day for each ad (in USD)
    # This minimum value is 1 USD for the currencies listed, and 0.5 USD for all others
    # https://developers.facebook.com/community/threads/812996445800356/
    # https://developers.facebook.com/docs/marketing-api/reference/ad-campaign#create-considerations
    limit_1usd = ['USD', 'AUD', 'CAD', 'SGD', 'JPY', 'NZD', 'TWD', 'EUR', 'CHF', 'SEK', 'HKD', 'GBP', 'ILS', 'NOK', 'KRW', 'DKK']
    df = df.copy()
    # get duration as integer (in days)
    # multiply by correct factor (calculated from currency)
    df['min_spend_USD_by_duration'] = df.duration * df.currency.isin(limit_1usd).apply(lambda x: 1 if x else 0.5)
    return df

def get_spend_lower_bound(df):
    '''
    Calculates the lower bound on the spend based on the two data sources we have:
    1) The lower value of the spend range given by the API; this is 0 for the lowest spend bin (common)
    2) The duration of the ad - all ads have a daily spend (usually 1 USD)
    The true spend cannot be lower than (2) (unless the ad is paused, but we have no information on this)
    However, the value in (1) is accurate, so is used as the lower bound if greater than (2)
    '''
    df = df.copy()
    df['spend_lower_bound_USD'] = df[['spend_lower_USD', 'min_spend_USD_by_duration']].max(axis=1)
    return df

def preproc(df):
    df = df.copy()
    df = make_datetime(df)
    df = split_range_fields(df)
    df = convert_spend_cols(df)
    df = calculate_duration(df)
    df = get_min_spend_by_duration(df)
    df = get_spend_lower_bound(df)
    # df = get_daily_spend_lower_bound(df)
    return df


### functions useful for analysis

# get ids of all ads active on each date in a list
def get_daily_active(df, dates):
    return {d : df.loc[((df.ad_delivery_start_time <= d) & (df.ad_delivery_stop_time >= d))].index for d in dates}

def get_daily_active_matrix(df, dates):
    '''
    input: standard ads dataframe
    output: dataframe with index ad id and columns dates
    element is true if the row's ad is active on the column's date
    '''
    daily_active = get_daily_active(df, dates) # get dict (date, active ids pairs)
    return pd.DataFrame(np.vstack([df.index.isin(daily_active[d]) for d in dates]).T, index=df.index, columns=dates)

def get_daily_spend_matrix(df, daily_active_matrix, spend_col, duration_col='duration'):
    return (daily_active_matrix.astype(int).T * (df[spend_col] / df[duration_col])).T.round(2)

# https://stackoverflow.com/a/45846841
def human_format(num):
    '''
    returns the number num in a human readable format (e.g. 123,000,000 --> 123M)
    '''
    num = float('{:.3g}'.format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T'][magnitude])

def get_regional_impressions(df, impressions_col, region_delivery_col='delivery_by_region'):
    return df.apply(
        lambda row: {d.get('region') : int(float(d.get('percentage')) * row[impressions_col]) \
                     for d in row[region_delivery_col] \
<<<<<<< HEAD
                     if float(d.get('percentage')) > 0 } if isinstance(row['delivery_by_region'], list) else np.nan,
        axis=1)
    return pd.Series(regional_impressions).apply(pd.Series).round()

import json
def get_country_impressions(df, impressions_col, region_delivery_col='delivery_by_region'):
    impressions_by_region = get_regional_impressions(df, impressions_col, region_delivery_col)

    with open('region_countries.json', 'r') as f:
        region_countries = json.load(f)
    
    impressions_by_country = impressions_by_region.T.groupby(region_countries).sum().T
    return impressions_by_country

from scipy.stats.mstats import rankdata
def get_percentiles(s):
    '''
    Get percentile for each value in a series
    return as a series (i.e. with the same indexing)
    '''
    return pd.Series(rankdata(s) / len(s), index=s.index)
=======
                     if float(d.get('percentage')) > 0 } if (isinstance(row['delivery_by_region'], list) and not pd.isna(row[impressions_col])) else np.nan,
        axis=1)
>>>>>>> parent of 3ce9137 (preprocessing updates)
