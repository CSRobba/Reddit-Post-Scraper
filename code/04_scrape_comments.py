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
CODE_NAME = "scrape_comments"
WORK_DIR = "../"

# ArcticPush URL
BASE_URL = "https://arctic-shift.photon-reddit.com/api/comments/search"

# Task 1: make list function to get ID of all relevant posts -- 'y'
  # Reading all json files in the raw folder
  # Check if they are "revlevant"
  # If they are relevant, then storing their IDs so that we can later get the comments
  # of those posts.

def get_pushpull_comment_ids(post_id):
  # Fetch Comment IDs for this post
  try:
    params = {
        "link_id": post_id
    }
    c_resp = requests.get(BASE_URL, params = params)
    comment_ids = c_resp.json().get('data', [])
    print(comment_ids[2])
    print(comment_ids[1])
    print(comment_ids[0])
  except Exception as e:
      comment_ids = []
      print(e)

  return comment_ids

# Task 2: Once we've gotten the comments, take only the relevant fields as defined below:
# relevant fields: 'author', 'body', 'controversiality', 'created_utc', 
# 'downs', 'id', 'likes' (maybe), 'link_id', 'parent_id', 'permalink' (reddit link), 'replies' (maybe)
# 'ups'

# Task 3: Save the comment in a json file based on the id of the comment, and the id of the parent.

if __name__ == "__main__":
    id = "1abbrew"
    get_pushpull_comment_ids(id)