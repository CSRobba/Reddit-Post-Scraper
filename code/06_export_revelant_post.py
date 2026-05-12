from langdetect import detect, DetectorFactory
import logging
import matplotlib.pyplot as plt
import numpy
import pandas
import os
import random
import requests
import sys
import time
from tqdm import tqdm
import util

#### GLOBAL VARIABLES #### 
CODE_NAME = "export_relevant_posts"
WORK_DIR = "../"
RAW_FOLDER = os.path.join(WORK_DIR, "data/raw/")
POSTS_FOLDER = os.path.join(RAW_FOLDER, "data/raw/posts")
COMMENTS_FOLDER = os.path.join(RAW_FOLDER, "data/raw/comments")

def relevant_posts():
    posts = []
    if os.path.exists(POSTS_FOLDER):
        for fname in os.listdir(POSTS_FOLDER):
            data = util.read_json(os.path.join(POSTS_FOLDER, fname))
            data["filename"] = fname
            data["body"] = data.get("body", "").strip().lower()
            
            # Make sure that the body contains at least five words
            if len(data["body"].split(" ")) > 5:
                ratings = data.get("relevance_rate", {})
                if "y" in ratings.values():
                    posts.append(data)
                    print(data)
                    break

if __name__ == '__main__':
    relevant_posts()
