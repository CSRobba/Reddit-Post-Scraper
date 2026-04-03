from glob import glob
from pathlib import Path
import pandas
import re

def parse_scrape_log_to_df(log_path):
    """Parse a scrape log into a pandas DataFrame."""
    p_start = re.compile(
        r"Starting scrape from (?P<subreddit>\S+) beginning (?P<start>\d{4}-\d{2}-\d{2}) to (?P<end>\d{4}-\d{2}-\d{2})"
    )
    p_proc = re.compile(
        r"Processing Term[s]?:\s*(?P<query_term>.+?):\s*Found (?P<potential_count>\d+) potential matches"
    )
    p_valid = re.compile(
        r"Validating Term[s]?:\s*(?P<query_term>.+?):\s*Found (?P<valid_count>\d+) valid match(?:es)?"
    )

    rows = []
    current = {"subreddit": None, "start": None, "end": None}
    pending = {}

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            m = p_start.search(line)
            if m:
                current = {
                    "subreddit": m.group("subreddit"),
                    "start": m.group("start"),
                    "end": m.group("end"),
                }
                pending.clear()
                continue

            m = p_proc.search(line)
            if m and current["subreddit"] is not None:
                term = m.group("query_term").strip()
                pending[term] = {
                    "subreddit": current["subreddit"],
                    "start": current["start"],
                    "end": current["end"],
                    "query_term": term,
                    "potential_count": int(m.group("potential_count")),
                    "valid_count": None,
                }
                continue

            m = p_valid.search(line)
            if m and current["subreddit"] is not None:
                term = m.group("query_term").strip()
                if term in pending:
                    pending[term]["valid_count"] = int(m.group("valid_count"))
                    rows.append(pending.pop(term))
                else:
                    rows.append(
                        {
                            "subreddit": current["subreddit"],
                            "start": current["start"],
                            "end": current["end"],
                            "query_term": term,
                            "potential_count": None,
                            "valid_count": int(m.group("valid_count")),
                        }
                    )

    df = pandas.DataFrame(
        rows,
        columns=[
            "subreddit",
            "start",
            "end",
            "query_term",
            "potential_count",
            "valid_count",
        ],
    )
    return df


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Parse Reddit scraper log file into CSV")
    parser.add_argument("--log_path", default="", help="Path to the log file")
    parser.add_argument("--output_csv", nargs="?", default="scrape_summary.csv", help="Output CSV path")
    ns = parser.parse_args()

    if ns.log_path == "":
        log_paths = [p for p in Path("../../logs/").glob("260[3-4]*.log")]
        print(log_paths)
        result_dfs = []
        for log_path in log_paths:
            print(log_path)
            result_df = parse_scrape_log_to_df(log_path)
            result_dfs.append(result_df)
        result_df = pandas.concat(result_dfs, ignore_index=True).drop_duplicates().reset_index(drop=True)
        result_df = result_df[(result_df["valid_count"] < result_df["potential_count"]) & (result_df["potential_count"] > 0)].reset_index(drop=True)
        result_df.to_csv(ns.output_csv, index=False)
        print(f"Wrote {len(result_df)} rows to {ns.output_csv}")
