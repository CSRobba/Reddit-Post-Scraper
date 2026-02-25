## Reddit-Post-Scraper
Scrape posts from Reddit that ask questions about AI's environmental Impact.

### Directory Details

**colabFiles/**  
Contains Google Colab notebooks used for the scraping pipeline:

- **scrape_reddit.ipynb**  
  Connects to the Reddit API, searches relevant subreddits, and collects posts related to AI’s environmental impact. Exports raw data for further processing.

- **process_submissions.ipynb**  
  Cleans and processes scraped data, filters relevant posts, and prepares structured datasets for analysis or research use.

**code/**  
  Contains python files. These are more up-to-date and structured than the Google Colab files.

- **util.py**  
  Contains functions that are useful throughout our codebase.

- **identify_subreddits.py**  
  Connects to the PushPull.io API. This API scrapes across subreddits for posts related to AI's environmental footprint. It identifies common subreddits of those posts in ```subreddits.json'''.

**logs/**  
  Contains the log history of the code. This maintains constant documentation of what has been done.

**README.md**  
Provides documentation, repository structure, and usage instructions.

### Testing Your Code
- **Suggested Workflow:**
  - Create a branch from main
  - Make desired code changes
  - Commit and push to your feature branch with clear commit message
  - Open the notebook in Colab using the “Open in Colab” button
  - Run the notebook to test your changes
  - If changes improve scraping behavior, open a pull request to merge into main
- **IMPORTANT:**
  Colab runs a temporary copy of the notebook.
  Do not make permanent edits in Colab unless you save them back to GitHub.
