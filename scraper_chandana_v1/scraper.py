import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import *

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

posts = []

for keyword in KEYWORDS:
    print(f"Searching: {keyword}")

    url = f"https://old.reddit.com/r/all/search/?q={keyword}&restrict_sr=0"
    r = requests.get(url, headers=HEADERS)

    print("Status code:", r.status_code)

    soup = BeautifulSoup(r.text, "html.parser")

    for post in soup.select("a.search-title"):
        title = post.text.strip()
        link = post["href"]

        posts.append({
            "keyword": keyword,
            "title": title,
            "url": link
        })

    time.sleep(3)

df = pd.DataFrame(posts)
df.drop_duplicates(subset="url", inplace=True)

print("ROWS SCRAPED:", len(df))

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
