from datetime import datetime, timedelta
import itertools
import json
from langdetect import detect, DetectorFactory
import logging
import matplotlib.pyplot as plt
import numpy
import pandas
import os
import requests
import sys
import time
from tqdm import tqdm
import util

#### GLOBAL VARIABLES #### 
CODE_NAME = "identify_subreddits"
WORK_DIR = "../"
CONFIG_FILE = os.path.join(WORK_DIR, "config.json")
QUERIES_FILE = os.path.join(WORK_DIR, "subreddit_queries.csv")
SUBREDDITS_FILE = os.path.join(WORK_DIR, "subreddits.json")

# PushPull URL
BASE_URL = "https://api.pullpush.io/reddit/search/submission/"

# PushPull Scraping Interval
INTERVAL = 30 # Unit: days
START = datetime(2022, 11, 30)
END = datetime(2026, 2, 1)

###### SELECT THE MOST COMMON SUBREDDITS ###### 
def top_subreddits():
   subreddits = util.read_json(SUBREDDITS_FILE)
   subreddits = pandas.DataFrame(
      zip(subreddits.keys(), subreddits.values()),
      columns = ["subreddit", "count"]
   )
   subreddits = subreddits.sort_values(by="count", ascending=False).reset_index(drop=True)
   
   print(len(subreddits))
   print(subreddits.head(n=int(len(subreddits)*0.1)))
   print(subreddits.head(n=int(len(subreddits)*0.1))['count'].mean())
   ax = plt.subplot() 
   subreddits.plot(kind="bar", ax=ax)
   plt.show()
   
   print(f"Distribution 75th Percentile: {numpy.percentile(subreddits['count'], 25)}")
   print(f"Distribution 90th Percentile: {numpy.percentile(subreddits['count'], 10)}")
   print(f"Mean: {subreddits['count'].mean()}")
   print(f"Std: {subreddits['count'].std()}")

   current_subreddits = util.read_json(CONFIG_FILE)["subreddits"]
   print(f"Length of current subreddits: {len(current_subreddits)}")
   print(f"Subreddits captured, but not in current: {', '.join([x for x in subreddits.head(n=int(len(subreddits)*0.2))['subreddit'].values if x not in current_subreddits])}")
   print(f"Subreddits in current, but not in captured: {', '.join([x for x in current_subreddits if x not in subreddits.head(n=int(len(subreddits)*0.2))['subreddit'].values])}")

###### PROCESS REQUEST ######
def process_request(data, params, logger):

   # Count how many of the potential posts are valid
   num_valid_data = 0
   for post in data:
      title = post.get('title', '')
      body = post.get('selftext', '')
      
      if util.is_english(post.get('title', '')) and len(body) > 5:
         num_valid_data += 1
         subreddit = post.get('subreddit')
         
         with open(SUBREDDITS_FILE, 'r') as file:
            subreddits = json.load(file)
            subreddits[subreddit] = subreddits.get(subreddit, 0) + 1

            with open(SUBREDDITS_FILE, 'w', encoding='utf-8') as f:
               json.dump(subreddits, f, indent=4)
   
   logger.info(f"Validating Term: {params['title']}: Found {num_valid_data} valid match(es).")
   return num_valid_data

###### RUN QUERIES ######
def run_queries(queries, logger):
    for indx, row in tqdm(queries.iterrows(), total=queries.shape[0]):
        if row["count"] == -1:
            row = util.run_pullpush_query(row, BASE_URL, process_request, logger)
            queries.at[indx, "count"] = row["count"]
            queries.to_csv(QUERIES_FILE)
            time.sleep(4)
    return queries

if __name__ == "__main__":
    # Read the config file. This contains search keywords.
    config = util.read_json(CONFIG_FILE)
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
    queries["subreddits"] = ""
    queries = queries.sort_values(by = "count", ascending = False).reset_index(drop = True)
    queries = queries.drop_duplicates(subset=["ai", "env", "start", "end"], keep="first").reset_index(drop = True)
    
    queries = run_queries(queries, logger)
    top_subreddits()