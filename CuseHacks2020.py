import csv
import googlemaps
from googlemaps.places import places_autocomplete_query
import datetime
import pandas as pd
import numpy as np
import urllib3, requests, json
import pandas as pd
import twitter
import urllib
import os
import pymongo
from urllib.error import URLError
from http.client import BadStatusLine
from urllib.parse import unquote

CONSUMER_KEY = 'rRXATpsIQezxlb9MLoYThqmbt'
CONSUMER_SECRET = 'ScOhM4xP9IiAnER58vs7kQ2F4j49rsbCaqNBHnSHINM1AikDLL'
OAUTH_TOKEN = '1177256824929755137-VPMHtVirzFflJgtS6zTCpxcDw2wVk4'
OAUTH_TOKEN_SECRET = 'FOUc8ZBgdO2hqUwlENcey2kXYjkOs5pQpRSdVQ7KaUlMX'
auth = twitter.oauth.OAuth(OAUTH_TOKEN, OAUTH_TOKEN_SECRET,
                               CONSUMER_KEY, CONSUMER_SECRET)

twitter_api = twitter.Twitter(auth=auth)    

##q = '#impeachment' # max 500 characters
##count = 100 # max = 100, default = 15
###See https://developer.twitter.com/en/docs/tweets/search/api- reference/get-search-tweets
##search_results = twitter_api.search.tweets(q=q,count=count)
##statuses = search_results['statuses']
### You can access each tweet in this ways
##for tweet in [status['text'] for status in statuses]:
##    print (tweet)

def twitter_search(twitter_api, q, max_results=2000, **kw):

    # See https://developer.twitter.com/en/docs/tweets/search/api-reference/get-search-tweets
    # and https://developer.twitter.com/en/docs/tweets/search/guides/standard-operators
    # for details on advanced search criteria that may be useful for 
    # keyword arguments

    # See https://dev.twitter.com/docs/api/1.1/get/search/tweets    
    search_results = twitter_api.search.tweets(q=q, count=10000,until = '2020-02-16', **kw)

    statuses = search_results['statuses']

    # Iterate through batches of results by following the cursor until we
    # reach the desired number of results, keeping in mind that OAuth users
    # can "only" make 180 search queries per 15-minute interval. See
    # https://developer.twitter.com/en/docs/basics/rate-limits
    # for details. A reasonable number of results is ~1000, although
    # that number of results may not exist for all queries.

    # Enforce a reasonable limit
    max_results = min(10000, max_results) 
    for _ in range(10000): # 10*100 = 1000
        try:
            next_results = search_results['search_metadata']['next_results']
        except KeyError as e: # No more results when next_results doesn't exist
            break
        # Create a dictionary from next_results, which has the following form:
        # ?max_id=313519052523986943&q=NCAA&include_entities=1
        kwargs = dict([ kv.split('=') 
                        for kv in next_results[1:].split("&") ])

        search_results = twitter_api.search.tweets(**kwargs)
        statuses += search_results['statuses']

        if len(statuses) > max_results: 
            break

    return statuses

q = "#Coronavirus"
tweets = twitter_search(twitter_api, q, max_results=1000, result_type='recent') #lang='zh'
data = pd.DataFrame(data=[i['text'] for i in tweets if 'retweeted_status' not in i], columns=['Tweets'])
l = ['id', 'text', 'coordinates', 'place', 'lang']
data['ID'] = np.array([tweet['id'] for tweet in tweets if 'retweeted_status' not in tweet])
data['location'] = np.array([tweet['user']['location'] for tweet in tweets if 'retweeted_status' not in tweet])
data['UID'] = np.array([tweet['user']['id'] for tweet in tweets if 'retweeted_status' not in tweet])

data.to_csv("scraped_tweets.csv")

import googlemaps
from googlemaps.places import places_autocomplete_query

gmaps = googlemaps.Client('AIzaSyAuEfZdOLsxWl41KbysoZMy6rcjHIM3hc8')

with open("scraped_tweets.csv", 
                encoding="cp1252", errors='ignore') as csvfile1, \
            open("filtered_tweets_test.csv", "w", newline='\n') as csvfile2:
        reader = csv.DictReader(csvfile1)
        writer = csv.DictWriter(csvfile2, fieldnames=['location', 'text', 'tweetid', 'userid'])
        writer.writeheader()
        for row in reader:
            try:
                location = row["location"]
                g = gmaps.geocode(places_autocomplete_query(gmaps, location))
                if g != []:
                    g_location = g[0]
                    row["location"] = g_location['formatted_address']
                    writer.writerow(row)
            except Exception:
                continue
        csvfile1.close()
        csvfile2.close()

        filepath = 'filtered_tweets_test.csv'
        clean_df = pd.read_csv(filepath, sep = ",", encoding='cp1252')
        clean_df['location'] = clean_df['location'].str.replace(',','')
        clean_df['text'] = clean_df['text'].str.replace('\t','')
        clean_df['text'] = clean_df['text'].str.replace('\n','')
        clean_df.head(20)
        clean_df = clean_df.replace([np.inf, -np.inf], np.nan)
        clean_df.isna().any(axis=0)
        clean_df.to_csv('processed_filtered_tweets_test.csv')

# NOTE: generate iam_token and retrieve ml_instance_id based on provided documentation  
header = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + "QRN__W9Bx49U79NwyMvWiAt_HHL659MNnEKO5dsIAK39", 'ML-Instance-ID': "7ee00ccd-985d-4d5e-b163-f33410f3909b"}
# NOTE: manually define and pass the array(s) of values to be scored in the next line
with open("processed_filtered_tweets_test.csv", 
        encoding="cp1252", errors='ignore') as csvfile:
    reader = csv.DictReader(csvfile)
    arr = [row for row in reader]
payload_scoring = {"input_data": [{"fields": ["Unnamed: 0", "location", "text", "tweetid", "userid"], "values": arr}]}
response_scoring = requests.post('https://us-south.ml.cloud.ibm.com/v4/deployments/82f1e9e9-8dc9-4a0d-9d95-3c1051c9960c/predictions', json=payload_scoring, headers=header)
print("Scoring response")
print(json.loads(response_scoring.text))

        