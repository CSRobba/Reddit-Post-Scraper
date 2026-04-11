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
  except Exception as e:
      comment_ids = []
      print(e)

  return comment_ids

# relevant fields: 'author', 'body', 'controversiality', 'created_utc', 
# 'downs', 'id', 'likes' (maybe), 'link_id', 'parent_id', 'permalink' (reddit link), 'replies' (maybe)
# 'ups'

# ----------------------------

# This function serves to populate a list of relevant post ID's from the rated
# files in the raw directory
def get_relevant_post_ids(raw_dir_path):
    
    relevant_ids = []
    # iterate through all files in raw directory (make sure to pass in correct path)
    # skip non-json files
    for filename in os.listdir(raw_dir_path):
        if not filename.endswith(".json"):
            continue
        
        file_path = os.path.join(raw_dir_path, filename)

        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            # get relevance_rate dict
            relevance_dict = data.get("relevance_rate", {})

            # check if any annotator marked 'y' (we can decide what to do with maybes)
            if any(val == "y" for val in relevance_dict.values()):
                post_id = data.get("id")
                if post_id:
                    relevant_ids.append(post_id)

        except Exception as e:
            print(f"Error reading {filename}: {e}")

    return relevant_ids

# Main
# Output stored in raw_comments
# currently posts with no comments are stored as empty files 
# (kept the epty files to track which posts have been processed)
if __name__ == "__main__":
  raw_dir_path = os.path.join(WORK_DIR, "raw")  # adjust if needed (this resolves to "../raw")
  output_dir = os.path.join(WORK_DIR, "raw_comments")

  ids = get_relevant_post_ids(raw_dir_path)

  print(f"Found {len(ids)} relevant posts")
  os.makedirs(output_dir, exist_ok=True)

  for post_id in ids:   # start smaller if crash (like ids[20])
    output_path = os.path.join(output_dir, f"{post_id}.json")

    if os.path.exists(output_path): #avoid duplicatation when re-running code
      print(f"Skipping {post_id} (already exists).")
      continue

    comments = get_pushpull_comment_ids(post_id)

    # save to file
    with open(output_path, "w") as f:
      json.dump(comments, f, indent=2)

    print(f"Saved {len(comments)} comments for {post_id}")

    #avoid hitting API too fast
    time.sleep(.2)