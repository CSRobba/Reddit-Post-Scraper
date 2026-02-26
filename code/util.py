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
import traceback

###### Read Config Logger ######
def read_json(file):
    with open(file, 'r') as f:
        data = json.load(f)
        return data

###### Initialize Logger ######
def initialize_logger(log_file = "./logs/log.log"):
    """
    Initializes the logger for our code. 

    Parameters:
    log_file: The path for the file that will contain our code logs. Default: ./logs/log.log
    """
    # 1. Create the logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # 2. Create the format
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

    # 3. File Handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)

    # 4. Stream Console Handler
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    # 5. Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger

###### FORMAT ISODATE ######
def format_isodate_to_date(dt):
   dt_obj = datetime.fromisoformat(dt).date()
   df_string = dt_obj.strftime('%Y_%m_%d')
   return df_string

###### IS ENGLISH ######
def is_english(text):
    try:
        return detect(text) == 'en'
    except:
        return False

###### Generate Queries Dataset ######  
def _generate_queries_all(**kwargs):
  """
  Creates dataset of all the queries that we have to run by finding the cross-product of all possible
  AI-related keywords, environmental keywords, and dates.
  """
  config = kwargs.get("config", {}) #read_json("../config.json"))
  start = kwargs.get("start", datetime(2022, 11, 30))
  end = kwargs.get("end", datetime(2026, 2, 1))
  interval = kwargs.get("interval", 10)

  ai_terms = config["keywords"]["ai"]
  env_terms = config["keywords"]["env"]
  subreddits = config.get("subreddits", [""])
  
  # create dates from the ```start''' date until the  ```end''' date, with ```interval''' days in between
  date_range = pandas.date_range(start, end, freq=f"{interval}D")

  queries = pandas.DataFrame(
      list(itertools.product(ai_terms, env_terms, date_range, subreddits)), 
      columns = ["ai", "env", "start", "subreddits"])
  queries["end"] = queries["start"] + timedelta(interval)

  return queries

###### Generate Queries Already Completed ###### 
def _generate_queries_already_run(queries_file = "./queries_run.csv", **kwargs):
  """
  Returns dataset of queries already run. Queries that have already been run are within a .csv file.
  Otherwise returns an empty dataframe.
  """
  
  if os.path.isfile(queries_file):
    queries_run = pandas.read_csv(queries_file)
    queries_run = queries_run.drop("Unnamed: 0", axis = 1)
    queries_run["start"] = pandas.to_datetime(queries_run["start"])
    queries_run["end"] = pandas.to_datetime(queries_run["end"])
    queries_run["subreddits"] = queries_run["subreddits"].astype(str)
    return queries_run

  return pandas.DataFrame([], columns = ["ai", "env", "start", "end", "subreddits", "count"])

###### Generate Queries Dataset ###### 
def generate_queries(queries_file = "./queries_run.csv", **kwargs):
   """
   Returns dataset of all the queries that have been run, and still need to be run. Those that have been
   already run will contain a non-negative entry in the "count" column. Those that still been to be processed
   will contain a -1 value in the "count" column.
   """
   
   queries_all = _generate_queries_all(**kwargs)
   queries_run = _generate_queries_already_run(queries_file, **kwargs)
   queries_all = queries_all.merge(queries_run,
                                     how = "left",
                                     on = ["ai", "env", "start", "end", "subreddits"])
   queries_all = queries_all.infer_objects(copy=False).fillna(-1)
   
   return queries_all

def send_request(params, base_url, process_request, logger):
   try:
    response = requests.get(base_url, params=params)
    response.raise_for_status()
    
    data = response.json().get('data', [])
    logger.info(f"Processing Term: {params['title']}: Found {len(data)} potential matches.")
    
    return process_request(data, params, logger)
   
   except Exception as e:
    logger.info(f"Error on {params['title']}: {e}")
    raise ValueError()

###### RUN ONE PULLPUSH QUERY ######
def run_pullpush_query(row, base_url, process_request, logger):
   after = int(row["start"].timestamp())
   before = int(row["end"].timestamp())
   logger.info(f"Starting scrape from {row['start'].date()} to {(row['end']).date()}...")
   
   params = {
     # include this tag if we want to only search in the title of the post
     'title': f"{row['ai']} {row['env']}",
     # include this tag if we want to only search in both title and body of the post
     # 'both': f"{row['ai']} {row['env']}",
     'after': after,
     'before': before,
     'size': 100,
     'sort': 'asc'
     }
   
   try:
    results = send_request(params, base_url, process_request, logger)
    row["count"] = results
   
   except ValueError as e:
      print(traceback.format_exc())

   return row

###### RUN ONE ARTICPUSH QUERY ######
def run_arcticpush_query(row, base_url, process_request, logger):
   after = int(row["start"].timestamp())
   before = int(row["end"].timestamp())
   subreddit = row["subreddits"]
   logger.info(f"Starting scrape from {subreddit} beginning {row['start'].date()} to {(row['end']).date()}...")
   
   params = {
     'subreddit': subreddit,
     # include this tag if we want to only search in the title of the post
     'title': f"{row['ai']} {row['env']}",
     # include this tag if we want to only search in both title and body of the post
     # 'query': f"{row['ai']} {row['env']}",
     'after': after,
     'before': before,
     'limit': 100,
     'sort': 'asc'
     }
   
   try:
    results = send_request(params, base_url, process_request, logger)
    row["count"] = len(results)
   
   except ValueError as e:
      print(traceback.format_exc())

   return row