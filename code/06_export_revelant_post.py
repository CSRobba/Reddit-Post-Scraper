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

app = Flask(__name__)
app.secret_key = "rater-secret-key-2024"