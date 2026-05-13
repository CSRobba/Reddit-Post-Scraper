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
import json
import html
import webbrowser

from collections import defaultdict
from datetime import datetime
from tqdm import tqdm
from jinja2 import Template
from markdown import markdown

from playwright.sync_api import sync_playwright
import shutil
import util

#### GLOBAL VARIABLES #### 
CODE_NAME = "export_relevant_posts"
WORK_DIR = "../"
RAW_FOLDER = os.path.join(WORK_DIR, "data/raw/")
POSTS_FOLDER = os.path.join(RAW_FOLDER, "posts")
COMMENTS_FOLDER = os.path.join(RAW_FOLDER, "comments")

EXPORT_FOLDER = os.path.join(WORK_DIR, "output")
HTML_FOLDER = os.path.join(EXPORT_FOLDER, "html")
PDF_FOLDER = os.path.join(EXPORT_FOLDER, "pdf")
INITIAL_CODING_FOLDER = os.path.join(EXPORT_FOLDER, "initial_open_coding")

os.makedirs(HTML_FOLDER, exist_ok=True)
os.makedirs(PDF_FOLDER, exist_ok=True)
os.makedirs(INITIAL_CODING_FOLDER, exist_ok=True)

HTML_TEMPLATE = """
    <!DOCTYPE html>
    <html>
    <head>

    <meta charset="utf-8">

    <title>{{ title }}</title>

    <style>

    body{
        font-family: Arial, sans-serif;
        background:#dae0e6;
        margin:0;
        padding:30px;
    }

    .container{
        max-width:900px;
        margin:auto;
    }

    .post{
        background:white;
        padding:20px;
        border-radius:8px;
        margin-bottom:20px;
    }

    .subreddit{
        color:#787c7e;
        font-size:13px;
    }

    .title{
        font-size:30px;
        font-weight:bold;
        margin-top:10px;
    }

    .meta{
        color:#787c7e;
        font-size:13px;
        margin-top:8px;
    }

    .body{
        margin-top:20px;
        font-size:16px;
        line-height:1.6;
        white-space:pre-wrap;
    }

    .comments{
        background:white;
        padding:20px;
        border-radius:8px;
    }

    .comment{
        border-left:2px solid #edeff1;
        padding-left:12px;
        margin-top:20px;
    }

    .comment-meta{
        color:#787c7e;
        font-size:12px;
        margin-bottom:8px;
    }

    .comment-body{
        font-size:14px;
        line-height:1.5;
    }

    .author{
        font-weight:bold;
        color:#1c1c1c;
    }

    </style>

    </head>

    <body>

    <div class="container">

    <div class="post">

    <div class="subreddit">
    r/{{ subreddit }}
    </div>

    <div class="title">
    {{ title }}
    </div>

    <div class="meta">
    Posted by u/{{ author }}
    •
    {{ created }}
    •
    {{ score }} points
    •
    {{ num_comments }} comments
    </div>

    <div class="body">
    {{ body }}
    </div>

    </div>

    <div class="comments">

    <h2>Comments</h2>

    {{ comments_html }}

    </div>

    </div>

    </body>
    </html>
"""

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
    
    print(f"Number of Posts Identified: {len(posts)}.")
    return posts

def deduplicate_posts(posts):

    df_posts = pandas.DataFrame(posts)
    df_posts = (
        df_posts
        .drop_duplicates(subset=["id", "title", "body"], keep="first")
        .reset_index(drop = True)
    )
    print(f"Number of Deduplicated Posts: {len(df_posts)}.")
    return df_posts

def post_comments(post_id):
    path = os.path.join(COMMENTS_FOLDER, f"{post_id}.json")
    if not os.path.exists(path):
        return []
    return util.read_json(path)

def build_comment_tree(comments):
    comments_by_id = {}
    children = defaultdict(list)
    
    for c in comments:
        c["children"] = []
        comments_by_id[c["name"]] = c

    roots = []
    
    for c in comments:
        parent_id = c.get("parent_id")
        if parent_id and parent_id.startswith("t1_"):
            if parent_id in comments_by_id:
                children[parent_id].append(c)
        else:
            roots.append(c)
    
    for parent_id, child_comments in children.items():
        comments_by_id[parent_id]["children"] = child_comments
        
    return roots

def format_timestamp(ts):

    if not ts:
        return ""

    return datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M UTC")

def render_comment(comment, depth=0):
    author = html.escape(comment.get("author", "[deleted]"))
    body = comment.get("body", "")
    body = html.escape(body)
    body = body.replace("\n", "<br>")
    score = comment.get("score", 0)
    created = format_timestamp(comment.get("created_utc"))

    children_html = ""

    for child in comment.get("children", []):
        children_html += render_comment(child, depth + 1)

    return f"""
        <div class="comment" style="margin-left:{depth * 24}px">
            <div class="comment-meta">
                <span class="author">u/{author}</span>
                •
                <span>{score} points</span>
                •
                <span>{created}</span>
            </div>

            <div class="comment-body">
                {body}
            </div>

            {children_html}
        </div>
    """

def generate_html(post, comments):

    roots = build_comment_tree(comments)
    comments_html = ""

    for root in roots:
        comments_html += render_comment(root)

    template = Template(HTML_TEMPLATE)

    html_output = template.render(
        subreddit=post.get("subreddit", ""),
        title=post.get("title", ""),
        author=post.get("author", ""),
        created=format_timestamp(post.get("created_utc")),
        score=post.get("score", 0),
        num_comments=post.get("num_comments", 0),
        body=html.escape(post.get("body", "")).replace("\n", "<br>"),
        comments_html=comments_html
    )

    return html_output

def html_to_pdf(html_path, pdf_path):

    with sync_playwright() as p:

        browser = p.chromium.launch()

        page = browser.new_page()

        page.goto(f"file://{os.path.abspath(html_path)}")

        page.pdf(
            path=pdf_path,
            format="A4",
            print_background=True,
            margin={
                "top": "20px",
                "bottom": "20px",
                "left": "20px",
                "right": "20px"
            }
        )

        browser.close()

def export_post(post_filename):
    post_path = os.path.join(POSTS_FOLDER, post_filename)
    post = util.read_json(post_path)
    post_id = post["id"]

    comments = post_comments(post_id)
    html_output = generate_html(post, comments)

    base_name = os.path.splitext(post_filename)[0]

    html_path = os.path.join(HTML_FOLDER, f"{base_name}.html")

    pdf_path = os.path.join(PDF_FOLDER, f"{base_name}.pdf")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_output)

    # Open in browser automatically
    webbrowser.open(f"file://{os.path.abspath(html_path)}")

    # Export PDF
    html_to_pdf(html_path, pdf_path)

    print(f"Exported:")
    print(f"HTML -> {html_path}")
    print(f"PDF  -> {pdf_path}")

def export_posts(post_filenames):
    for fname in tqdm(post_filenames):
        try:
            export_post(fname)
        except Exception as e:
            print(f"Failed on {fname}")
            print(e)

if __name__ == "__main__":
    posts = relevant_posts()
    posts = deduplicate_posts(posts)

    #filenames = list(posts["filename"].values)
    #export_posts(filenames)

    #choose random files for initial coding
    initial_coding_sample = posts.sample(n=50)
    for i, row in initial_coding_sample.iterrows():
        src = row['filename'].split(".json")[0] + ".pdf"
        shutil.copy2(os.path.join(PDF_FOLDER, src), os.path.join(INITIAL_CODING_FOLDER, f"chandana_{src}"))
        shutil.copy2(os.path.join(PDF_FOLDER, src), os.path.join(INITIAL_CODING_FOLDER, f"julie_{src}"))
        shutil.copy2(os.path.join(PDF_FOLDER, src), os.path.join(INITIAL_CODING_FOLDER, f"nino_{src}"))

