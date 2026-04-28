from datetime import datetime, timedelta
import itertools
import json
from langdetect import detect, DetectorFactory
import logging
import pandas
import os
import requests
import sys
import time
from tqdm import tqdm
import util

#### GLOBAL VARIABLES #### 
CODE_NAME = "scrape_subreddits"
WORK_DIR = "../"
QUERIES_FILE = os.path.join(WORK_DIR, "posts_queries.csv")
SUBREDDITS_FILE = os.path.join(WORK_DIR, "subreddits.json")

# ArcticPush URL
BASE_URL = "https://arctic-shift.photon-reddit.com/api/posts/search"
# ArcticPush Scraping Interval
INTERVAL = 365 # Unit: days q
START = datetime(2022, 11, 30)
END = datetime(2026, 4, 1)

###### RUN POST ######
def save_post(result):
    file_path = os.path.join(
        WORK_DIR, 
        f"raw/{result['id']}_{result['query_term'].replace(' ', '_').replace('-', '_').lower()}_{util.format_isodate_to_date(result['created'])}.json"
        )
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4)

###### PROCESS REQUEST RESULT ######
def process_request(data, params, logger):
    results = []
    
    for post in data:
        title = post.get('title', '')
        body = post.get('selftext', '')
        
        if util.is_english(post.get('title', '')): # Note: I had a condition **len(post.get('selftext', '')) > 5)** where I removed posts with short bodies. However, if we are interested in discourse analysis, then even posts with relevant titles, and their comments, should count. 
            post_id = post.get('id')
            
            result = {
                'query_term': params['title'],
                'title': title,
                'id': post_id,
                'body': post.get('selftext'),
                'url': post.get('url'),
                'url_overridden_by_dest': post.get('url_overridden_by_dest'),
                'created': datetime.fromtimestamp(post.get('created_utc')).isoformat(),
                'author': post.get('author'),
                'subreddit': post.get('subreddit'),
                'num_comments': post.get('num_comments'),
                'ups': post.get('ups'),
                'upvote_ratio': post.get('upvote_ratio'),
                'view_count': post.get('view_count')
            }
            save_post(result)
            results.append(result)
    
    logger.info(f"Validating Term: {params['title']}: Found {len(results)} valid match(es).")
    return results

###### RUN QUERIES ######
def run_queries(queries, logger):
    for indx, row in tqdm(queries.iterrows(), total=queries.shape[0]):
        if row["count"] == -1:
            row = util.run_arcticpush_query(row, BASE_URL, process_request, logger)
            queries.at[indx, "count"] = row["count"]
            queries.to_csv(QUERIES_FILE)
            time.sleep(4)
    return queries

if __name__ == "__main__":
    # Read the config file. This contains search keywords.
    config = util.read_json(f'{WORK_DIR}/config.json')
    # Create a logger for our code.
    now = datetime.now().strftime("%y%m%d%H%M")
    logger = util.initialize_logger(log_file = f"{WORK_DIR}/logs/{now}_{CODE_NAME}_log.log")
    
    queries_kwargs = {
       'config': config,
       'start': START,
       'end': END,
       'interval': INTERVAL
    }
    queries = util.generate_queries(queries_file = QUERIES_FILE, **queries_kwargs)

    queries = run_queries(queries, logger)