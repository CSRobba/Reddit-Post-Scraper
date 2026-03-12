# scraper_chandana_v1

This scraper collects Reddit posts containing specified keywords and uploads them to a shared Google Sheet (see below) for qualitative analysis.

Instead of using the official Reddit API, this tool retrieves publicly accessible search results from **old.reddit.com**, which serves static HTML pages that can be parsed reliably using Python.

Scraped results are written to the shared spreadsheet:

**Google Sheet Output:**  
[RedditScrape_v1](https://docs.google.com/spreadsheets/d/1SY5XGZBn8yUUdyfuyS3Gn0gOhtRVpqFPEYWcWH7oIss/edit?gid=0#gid=0)

---

# How It Works

1. The script queries **old.reddit.com search pages** for each keyword defined in `config.py`.
2. HTML search results are downloaded using the `requests` library.
3. Post titles and URLs are extracted using `BeautifulSoup`.
4. Duplicate posts are removed using `pandas`.
5. The cleaned dataset is uploaded to a Google Sheet via the Google Sheets API.

Pipeline:

Reddit Search → HTML Parsing → Data Cleaning → Google Sheets Upload

---

# Setup

### 1. Install Python

Python **3.10+** is recommended.

Check your version:

```bash
python --version
```

---

### 2. Install dependencies

From inside the `scraper_chandana_v1` folder:

```bash
pip install -r requirements.txt
```

---

### 3. Add Google API credentials (if you want to make another sheet)

This scraper uploads results to Google Sheets using a **Google Service Account**.

Steps:

1. Create a Google Cloud project
2. Enable:
   - Google Sheets API
   - Google Drive API
3. Create a **Service Account**
4. Download the key as:

```
credentials.json
```

---

### 4. Share the target Google Sheet (if you want to make another sheet)

The service account must be given access to the sheet.

Open `credentials.json` and copy the value of:

```
client_email
```

Then share the Google Sheet with that email and give it **Editor permissions**.

---

### 5. Configure keywords

Edit `config.py`:

```python
GOOGLE_SHEET_NAME = "RedditScrape_v1"

KEYWORDS = [
    "ai",
    "machine learning",
    "chatgpt"
]
```

---

### 6. Run the scraper

From inside the folder:

```bash
python scraper.py
```

The script will:

1. Search Reddit for each keyword
2. Collect matching posts
3. Remove duplicates
4. Upload results to the Google Sheet

---

# Responsible Use & Data Collection Notice

This tool collects **publicly accessible Reddit search results** from `old.reddit.com`.  
It does **not** access private subreddits, authenticated endpoints, or user accounts.

Requests are intentionally spaced with delays to minimize load on Reddit’s servers.

This scraper is intended for **educational and research purposes only**. Users should ensure their usage complies with Reddit’s Terms of Service and applicable laws.

The script does not attempt to bypass authentication systems or scrape protected content.

---

# Limitations

- Results depend on Reddit's search indexing.
- Only posts visible on public search pages can be collected.
- HTML structure changes on Reddit may require updates to the scraper.
- This tool is not intended or suitable for large-scale or high-frequency scraping.

---

# Folder Structure

```
scraper_chandana_v1/
│
├── scraper.py
├── config.py
├── requirements.txt
├── README.md
└── credentials.json (hidden, dont commit to repo)
```

---

# Note

This scraper is designed as an **independent prototype** within the repository so that multiple scraping approaches can be tested without interfering with other implementations.
