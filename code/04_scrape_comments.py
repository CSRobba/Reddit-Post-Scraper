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

# relevant fields: 'author', 'body', 'controversiality', 'created_utc', 
# 'downs', 'id', 'likes' (maybe), 'link_id', 'parent_id', 'permalink' (reddit link), 'replies' (maybe)
# 'ups'

if __name__ == "__main__":
    id = "1abbrew"
    get_pushpull_comment_ids(id)
    



# make list function to get ID of all relevant posts -- 'y'