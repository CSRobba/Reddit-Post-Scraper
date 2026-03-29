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

# ── Shared global progress cache (updated on every vote) ──────────────────────
_progress = None

def load_global_progress():
    global _progress
    total = completed = 0
    if os.path.exists(RAW_FOLDER):
        for fname in os.listdir(RAW_FOLDER):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(RAW_FOLDER, fname), encoding="utf-8") as f:
                    data = json.load(f)
                total += 1
                if len(data.get("relevance_rate", {})) >= 2:
                    completed += 1
            except Exception:
                pass
    _progress = {"completed": completed, "total": total}


def build_eligible(name):
    """Scan raw/ once and return list of filenames eligible for NAME."""
    eligible = []
    if not os.path.exists(RAW_FOLDER):
        return eligible
    for fname in os.listdir(RAW_FOLDER):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(RAW_FOLDER, fname), encoding="utf-8") as f:
                data = json.load(f)
            ratings = data.get("relevance_rate", {})
            if name not in ratings and len(ratings) < 2:
                eligible.append(fname)
        except Exception:
            pass
    return eligible


# ── HTML templates (inline) ───────────────────────────────────────────────────

BASE_STYLE = """
<style>
  body { font-family: sans-serif; max-width: 700px; margin: 40px auto; padding: 0 16px; color: #000; background: #fff; }
  a { color: #000; }
  input[type=text] { border: 1px solid #000; padding: 6px 8px; font-size: 15px; width: 260px; }
  button { border: 1px solid #000; background: #fff; padding: 6px 14px; font-size: 14px; cursor: pointer; }
  button:hover { background: #000; color: #fff; }
  hr { border: none; border-top: 1px solid #000; margin: 20px 0; }
  .progress-bar-track { width: 100%; height: 12px; border: 1px solid #000; margin-top: 4px; }
  .progress-bar-fill { height: 100%; background: #000; }
  .fixed-bottom { position: fixed; bottom: 0; left: 0; right: 0; background: #fff; border-top: 1px solid #000; padding: 10px 16px; }
  .fixed-bottom-inner { max-width: 700px; margin: 0 auto; }
  .vote-buttons { display: flex; gap: 10px; margin-top: 8px; }
  .vote-buttons button { flex: 1; padding: 10px; font-size: 15px; }
  body { padding-bottom: 110px; }
</style>
"""

INDEX_HTML = BASE_STYLE + """
<h2>Post Rater</h2>
<hr>
<form method="POST">
  <label>Your name:<br><br>
  <input type="text" name="name" required autofocus autocomplete="off"></label><br><br>
  <button type="submit">Start rating</button>
</form>
"""

DONE_HTML = BASE_STYLE + """
<h2>Post Rater</h2>
<hr>
<p>No more posts to rate, {name}. Either everything has been rated twice, or you've reviewed all available posts.</p>
<p><a href="/logout">Switch user</a></p>
"""

RATE_HTML = BASE_STYLE + """
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


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name:
            session["name"] = name
            session.pop("eligible", None)  # clear any stale list from a previous session
            return redirect(url_for("rate"))
    return INDEX_HTML


@app.route("/rate")
def rate():
    global _progress
    name = session.get("name")
    if not name:
        return redirect(url_for("index"))

    # Build eligible list once per session; pop from it on each vote
    if "eligible" not in session:
        session["eligible"] = build_eligible(name)
        if _progress is None:
            load_global_progress()

    eligible = session["eligible"]
    if not eligible:
        return DONE_HTML.format(name=name)

    chosen = random.choice(eligible)
    session["current_file"] = chosen

    fpath = os.path.join(RAW_FOLDER, chosen)
    with open(fpath, encoding="utf-8") as f:
        post = json.load(f)

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
        name=name,
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
    name = session.get("name")
    current_file = session.get("current_file")
    if not name or not current_file:
        return redirect(url_for("index"))

    vote = request.form.get("vote")
    if vote not in ("y", "n", "m"):
        return redirect(url_for("rate"))

    fpath = os.path.join(RAW_FOLDER, current_file)
    with open(fpath, encoding="utf-8") as f:
        data = json.load(f)

    if "relevance_rate" not in data:
        data["relevance_rate"] = {}
    data["relevance_rate"][name] = vote

    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    # Pop the just-rated file from the cached eligible list — no rescan needed
    eligible = session.get("eligible", [])
    if current_file in eligible:
        eligible.remove(current_file)
    session["eligible"] = eligible

    # Incrementally update global progress cache
    if _progress and len(data["relevance_rate"]) == 2:
        _progress["completed"] += 1

    return redirect(url_for("rate"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    load_global_progress()
    app.run(debug=True)