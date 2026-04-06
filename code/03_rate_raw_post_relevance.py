from datetime import datetime, timedelta
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import itertools
import json
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
CODE_NAME = "rate_raw_post_relevance"
WORK_DIR = "../"
RAW_FOLDER = os.path.join(WORK_DIR, "raw/")

app = Flask(__name__)
app.secret_key = "rater-secret-key-2024"

# Shared global progress cache (updated on every vote)
_progress = None
_eligible = None
_name = None
_current_file = None

def automatic_rating():
    global _name
    posts = []
    if os.path.exists(RAW_FOLDER):
        for fname in os.listdir(RAW_FOLDER):
            data = util.read_json(os.path.join(RAW_FOLDER, fname))
            data["filename"] = fname
            
            if data["body"] == "[removed]" or data["body"] == "[deleted]":
                if "relevance_rate" not in data:
                    data["relevance_rate"] = {}
                data["relevance_rate"][_name] = "n"
            
            ratings = data.get("relevance_rate", {})
            name_vote = -1
            if _name in ratings:
                name_vote = ratings.get(_name, -1)
                name_vote = 1 if name_vote == "y" else (0.5 if name_vote == "m" else 0)
            
            data["vote"] = name_vote
            posts.append(data)
    
    posts = pandas.DataFrame(posts)
    posts = posts.groupby(["title", "body"]).agg({"filename": "list", "vote": "max"}).reset_index()
    print(posts.head())

def load_global_progress():
    global _progress
    global _name
    total = completed = relevant = 0
    if os.path.exists(RAW_FOLDER):
        for fname in os.listdir(RAW_FOLDER):
            data = util.read_json(os.path.join(RAW_FOLDER, fname))
            total += 1
            if len(data.get("relevance_rate", {})) >= 2 or _name in data.get("relevance_rate", {}):
                completed += 1
                if "y" in list(data.get("relevance_rate", {}).values()) or "m" in list(data.get("relevance_rate", {}).values()):
                    relevant += 1 
        _progress = {"completed": completed, "total": total, "relevant": relevant}
        print(relevant, completed)

def build_eligible(name):
    """Scan ``raw/'' folder once and return list of filenames eligible for NAME."""
    global _eligible
    _eligible = []
    for fname in os.listdir(RAW_FOLDER):
        data = util.read_json(os.path.join(RAW_FOLDER, fname))
        ratings = data.get("relevance_rate", {})
        
        if name not in ratings and len(ratings) < 2:
            _eligible.append(fname)
    
    print(len(_eligible))

##########
# HTML
##########
INDEX_HTML = """
<h2>Post Rater</h2>
<hr>
<form method="POST">
  <label>Your name:<br><br>
  <input type="text" name="name" required autofocus autocomplete="off"></label><br><br>
  <button type="submit">Start rating</button>
</form>
"""

DONE_HTML = """
<h2>Post Rater</h2>
<hr>
<p>No more posts to rate, {name}. Either everything has been rated twice, or you've reviewed all available posts.</p>
<p><a href="/logout">Switch user</a></p>
"""

RATE_HTML = """
<p style="font-size:13px;color:#555;">Signed in as <strong>{name}</strong> &mdash; <a href="/logout">sign out</a></p>
<hr>

<p style="font-size:12px;color:#555;">r/{subreddit} &bull; u/{author} &bull; {created}</p>
<h2 style="margin:8px 0 12px;">{title}</h2>

<p style="font-size:14px;line-height:1.6;white-space:pre-wrap;">{body}</p>

{link_html}

<p style="font-size:12px;color:#555;margin-top:12px;">
  &#9650; {ups} &nbsp;&bull;&nbsp; {num_comments} comments &nbsp;&bull;&nbsp; {upvote_pct}% upvoted
</p>

{rated_note}

<hr>
<p style="font-size:13px;color:#555;">Query term: <em>{query_term}</em></p>

<div class="fixed-bottom">
  <div class="fixed-bottom-inner">
    <form method="POST" action="/submit">
      <div style="font-size:13px;font-weight:bold;">Is this post relevant to the query?</div>
      <div class="vote-buttons">
        <button name="vote" value="y">Yes</button>
        <button name="vote" value="m">Maybe</button>
        <button name="vote" value="n">No</button>
        <input type="text" id="reasoning" name="reasoning">
      </div>
    </form>
    <div style="margin-top:10px;font-size:12px;color:#555;">
      Overall progress: {completed}/{total} posts fully rated
      <div class="progress-bar-track">
        <div class="progress-bar-fill" style="width:{pct}%"></div>
      </div>
    </div>
  </div>
</div>
"""

##########
# Routes
##########
@app.route("/", methods=["GET", "POST"])
def index():
    global _name, _progress, _eligible
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name:
            session["name"] = name
            _name = name
            _progress = None
            _eligible = None
            return redirect(url_for("rate"))
    return INDEX_HTML

@app.route("/rate")
def rate():
    global _progress
    global _name
    global _eligible
    global _current_file

    automatic_rating()
    
    # Build eligible list once per session; pop from it on each vote
    if _eligible is None:
        build_eligible(_name)
    
    if _progress is None:
        load_global_progress()
    
    if len(_eligible)==0:
        return DONE_HTML.format(name=_name)

    chosen = random.choice(_eligible)
    _current_file = chosen
    
    print(chosen)
    print(_current_file)

    fpath = os.path.join(RAW_FOLDER, chosen)
    post = util.read_json(fpath)

    ratings = post.get("relevance_rate", {})
    rated_count = len(ratings)
    
    rated_note = (
        f'<p style="font-size:12px;color:#555;">{rated_count} other '
        f'rater{"s" if rated_count != 1 else ""} have already reviewed this post.</p>'
        if rated_count > 0 else ""
    )

    url = post.get("url_overridden_by_dest") or post.get("url") or ""
    link_html = (
        f'<p style="font-size:13px;margin-top:8px;"><a href="{url}" target="_blank" rel="noopener">'
        f'{url[:80]}{"&hellip;" if len(url) > 80 else ""}</a></p>'
        if url else ""
    )

    p = _progress or {"completed": 0, "total": 0}
    pct = round(p["completed"] / p["total"] * 100) if p["total"] else 0

    return RATE_HTML.format(
        name=_name,
        subreddit=post.get("subreddit", "unknown"),
        author=post.get("author", "unknown"),
        created=(post.get("created") or "")[:10],
        title=post.get("title", ""),
        body=post.get("body", ""),
        link_html=link_html,
        ups=post.get("ups", 0),
        num_comments=post.get("num_comments", 0),
        upvote_pct=int((post.get("upvote_ratio") or 0) * 100),
        rated_note=rated_note,
        query_term=post.get("query_term", ""),
        completed=p["completed"],
        total=p["total"],
        pct=pct,
    )

@app.route("/submit", methods=["POST"])
def submit():
    global _progress
    global _eligible
    global _name
    global _current_file

    print(f"Name: {_name}")
    print(f"Current File: {_current_file}")

    vote = request.form.get("vote")
    if vote not in ("y", "n", "m"):
        return redirect(url_for("rate"))

    reasoning = request.form.get("reasoning", "").strip()

    print(RAW_FOLDER)
    print(_current_file)
    fpath = os.path.join(RAW_FOLDER, _current_file)
    data = util.read_json(fpath)

    if "relevance_rate" not in data:
        data["relevance_rate"] = {}
    data["relevance_rate"][_name] = vote
    if reasoning:
        if "relevance_reasoning" not in data:
            data["relevance_reasoning"] = {}
        data["relevance_reasoning"][_name] = reasoning

    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    # Pop the just-rated file from the cached eligible list — no rescan needed
    if _current_file in _eligible:
        _eligible.remove(_current_file)
    
    # Incrementally update global progress cache
    _progress["completed"] += 1

    return redirect(url_for("rate"))

@app.route("/logout")
def logout():
    global _name, _progress, _eligible, _current_file
    session.clear()
    _name = None
    _progress = None
    _eligible = None
    _current_file = None
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)