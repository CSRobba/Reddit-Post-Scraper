import praw
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import *

reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT
)

keywords = ["ai", "machine learning", "chatgpt"]
subreddit = "all"
limit_per_keyword = 200

posts = []

for keyword in keywords:
    print(f"Searching: {keyword}")
    for submission in reddit.subreddit(subreddit).search(keyword, limit=limit_per_keyword):
        posts.append({
            "keyword": keyword,
            "title": submission.title,
            "text": submission.selftext,
            "subreddit": submission.subreddit.display_name,
            "score": submission.score,
            "url": submission.url
        })

df = pd.DataFrame(posts)
df.drop_duplicates(subset="url", inplace=True)

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "credentials.json", scope
)
client = gspread.authorize(creds)

sheet = client.open(GOOGLE_SHEET_NAME).sheet1
sheet.clear()
sheet.update([df.columns.values.tolist()] + df.values.tolist())

print("Upload complete.")
