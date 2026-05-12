from datetime import datetime, timedelta
from glob import glob
import itertools
import json
from langdetect import detect, DetectorFactory
import logging
from pathlib import Path
import pandas
import os
import requests
import sys
import time
from tqdm import tqdm
import util

#### GLOBAL VARIABLES #### 
CODE_NAME = "raw_post_to_csv"
WORK_DIR = "../"
RAW_DIR = os.path.join(WORK_DIR, "data/raw/posts")
QUERIES_FILE = os.path.join(WORK_DIR, "posts_queries.csv")
SUBREDDITS_FILE = os.path.join(WORK_DIR, "subreddits.json")
OUTPUT_DIR = os.path.join(WORK_DIR, "output/")
SUBMISSIONS_FILE = os.path.join(OUTPUT_DIR, "submissions.csv")

if __name__ == '__main__':

    submissions = []
    # search for the downloaded json files
    raw_posts = [r for r in glob(os.path.join(RAW_DIR, "*.json"))]
    
    # read the content in each file; save to `submissions` list
    for r in raw_posts:
        data = util.read_json(r)
        submissions.append(data)

    # convert submission list of dicts to a dataframe
    submissions = pandas.DataFrame(submissions)
    
    # save the file
    submissions.to_csv(SUBMISSIONS_FILE, index=False)
        




