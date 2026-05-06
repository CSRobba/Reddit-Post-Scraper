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
CODE_NAME = "review_rated_posts"
WORK_DIR = "../"
RAW_FOLDER = os.path.join(WORK_DIR, "raw/")

app = Flask(__name__)
app.secret_key = "rater-secret-key-2024"

# Shared global progress cache (updated on every vote)
_progress = None
_eligible = None
_name = None
_current_file = None
_filters = None  # list of selected filter values, e.g. ["y", "disagreement"]

def _make_list(x):
    T = tuple(x)
    return T

def automatic_rating():
    global _name
    posts = []
    if os.path.exists(RAW_FOLDER):
        for fname in os.listdir(RAW_FOLDER):
            data = util.read_json(os.path.join(RAW_FOLDER, fname))
            data["filename"] = fname
            data["body"] = data.get("body", "").strip().lower()
            
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
    posts = posts.groupby(["title"]).agg({"filename": _make_list, "vote": "max"}).reset_index()

    print(f"Number of de-duplicated posts: {posts.shape[0]}")
    rated_posts = posts[posts["vote"] != -1]
    num_ratings_added = 0
    for idx, row in rated_posts.iterrows():
        for fname in row["filename"]:
            fpath = os.path.join(RAW_FOLDER, fname)
            data = util.read_json(fpath)
            if "relevance_rate" not in data:
                data["relevance_rate"] = {}
            if _name not in data["relevance_rate"]:
                data["relevance_rate"][_name] = "y" if row["vote"] == 1 else ("m" if row["vote"] == 0.5 else "n")
                num_ratings_added += 1
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"Number of ratings added: {num_ratings_added}")

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
        print(f"Relevant: {relevant}, Completed: {completed}, Total: {total}")

def _post_matches_filters(data, filters):
    """Return True if the post should appear given the active filters.

    filters is a list that may contain any combination of "y", "m", "n", and
    "disagreement".  A post matches if it satisfies *any* of the selected
    filters (OR logic).

    If filters is empty (no checkboxes ticked) the function falls through to
    the standard unrated-post behaviour handled by build_eligible.
    """
    if not filters:
        return True  # no filter restriction — handled by caller

    ratings = data.get("relevance_rate", {})
    rating_values = list(ratings.values())
    unique_ratings = set(rating_values)

    for f in filters:
        if f == "disagreement":
            # Disagreement: at least two raters with different verdicts
            if len(unique_ratings) > 1:
                return True
        elif f in ("y", "m", "n"):
            # At least one rater gave this verdict
            if f in rating_values:
                return True

    return False

def build_eligible(name, filters=None):
    """Scan ``raw/'' folder once and return list of filenames eligible for NAME.

    When *filters* is non-empty the eligibility criteria change:
      - The post must satisfy at least one of the selected filters.
      - We no longer restrict to posts that NAME hasn't seen yet, so raters
        can browse/re-review filtered subsets freely.
    When *filters* is empty (default) the original behaviour is preserved:
      only posts that haven't been rated by NAME and haven't reached 2 ratings
      are included.
    """
    global _eligible
    _eligible = []

    if not os.path.exists(RAW_FOLDER):
        print("RAW_FOLDER does not exist.")
        return

    for fname in os.listdir(RAW_FOLDER):
        data = util.read_json(os.path.join(RAW_FOLDER, fname))
        ratings = data.get("relevance_rate", {})

        if filters:
            # Filter mode: include posts matching the filter criteria
            if _post_matches_filters(data, filters) and (_name in ratings.keys()):
                vote_filters = [f for f in filters if f in ("y", "m", "n")]
                has_disagreement_filter = "disagreement" in filters
                user_vote = ratings[_name]
                # Include if: user's vote matches a vote filter, OR
                # disagreement filter is active and this post has conflicting ratings
                if (vote_filters and user_vote in vote_filters) or \
                   (has_disagreement_filter and len(set(ratings.values())) > 1):
                    _eligible.append(fname)
        else:
            # Default mode: only unreviewed posts
            if name not in ratings and len(ratings) < 2:
                _eligible.append(fname)
    
    _eligible = list(set(_eligible))  # deduplicate just in case
    print(f"Number of eligible posts: {len(_eligible)}")

##########
# HTML
##########
INDEX_HTML = """
<h2>Post Rater</h2>
<hr>
<form method="POST">
  <label>Your name:<br><br>
  <input type="text" name="name" required autofocus autocomplete="off"></label><br><br>

  <label><strong>Filter posts to review</strong> (multi-select; leave all unchecked to see unrated posts):<br><br>
  <div style="display:flex;gap:20px;flex-wrap:wrap;margin-top:4px;">
    <label><input type="checkbox" name="filters" value="y"> Rated <strong>Yes</strong></label>
    <label><input type="checkbox" name="filters" value="m"> Rated <strong>Maybe</strong></label>
    <label><input type="checkbox" name="filters" value="n"> Rated <strong>No</strong></label>
    <label><input type="checkbox" name="filters" value="disagreement"> <strong>Disagreements</strong></label>
  </div>
  </label><br><br>

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
{filter_banner}
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
      Overall: {num_eligible} Number of Posts Matching Filters, {completed}/{total} Rated ({pct}%)
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
    global _name, _progress, _eligible, _filters
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        # getlist returns all checked values for the "filters" checkbox group
        filters = request.form.getlist("filters")
        if name:
            session["name"] = name
            session["filters"] = filters
            _name = name
            _filters = filters
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
    global _filters

    # Build eligible list once per session; pop from it on each vote
    if _eligible is None:
        automatic_rating()
        build_eligible(_name, filters=_filters)
    
    if _progress is None:
        load_global_progress()
    
    if len(_eligible) == 0:
        return DONE_HTML.format(name=_name)

    chosen = random.choice(_eligible)
    _current_file = chosen
    
    print(chosen)
    print(_current_file)

    fpath = os.path.join(RAW_FOLDER, chosen)
    post = util.read_json(fpath)

    ratings = post.get("relevance_rate", {})
    rated_count = len(ratings)
    
    reasoning = post.get("relevance_reasoning", {})
    rated_note = (
        f'<p style="font-size:12px;color:#555;">{rated_count} other '
        f'rater{"s" if rated_count != 1 else ""} have already reviewed this post.'
        + (
            "<ul style='margin:4px 0;padding-left:18px;'>"
            + "".join(
                f"<li><strong>{k}</strong>: {v}"
                + (f" &mdash; <em>{reasoning[k]}</em>" if k in reasoning else "")
                + "</li>"
                for k, v in ratings.items()
            )
            + "</ul>"
            if rated_count > 0 else ""
        )
        + "</p>"
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

    # Build a small banner showing active filters
    if _filters:
        label_map = {"y": "Yes", "m": "Maybe", "n": "No", "disagreement": "Disagreements"}
        labels = [label_map.get(f, f) for f in _filters]
        filter_banner = (
            f'<p style="font-size:12px;color:#777;margin:4px 0;">Filtering by: '
            f'<strong>{", ".join(labels)}</strong></p>'
        )
    else:
        filter_banner = ""

    return RATE_HTML.format(
        name=_name,
        filter_banner=filter_banner,
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
        num_eligible=len(_eligible)
    )

@app.route("/submit", methods=["POST"])
def submit():
    global _progress
    global _eligible
    global _name
    global _current_file
    global _filters

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

    # In filter mode, re-check whether the post still matches the active
    # filters after the new vote was cast (e.g. a disagreement may have been
    # resolved).  If it no longer matches, remove it from the eligible pool.
    if _filters:
        updated_data = util.read_json(fpath)
        if not _post_matches_filters(updated_data, _filters):
            if _current_file in _eligible:
                _eligible.remove(_current_file)
    else:
        # Default mode: pop the just-rated file — no rescan needed
        if _current_file in _eligible:
            _eligible.remove(_current_file)
    
    # Incrementally update global progress cache
    _progress["completed"] += 1

    return redirect(url_for("rate"))

@app.route("/logout")
def logout():
    global _name, _progress, _eligible, _current_file, _filters
    session.clear()
    _name = None
    _progress = None
    _eligible = None
    _current_file = None
    _filters = None
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)