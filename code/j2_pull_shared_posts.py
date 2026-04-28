import json
import os
import random

RAW_FOLDER = "../raw/"

agreements = []

for fname in os.listdir(RAW_FOLDER):
    fpath = os.path.join(RAW_FOLDER, fname)
    with open(fpath, encoding="utf-8") as f:
        data = json.load(f)

    ratings = data.get("relevance_rate", {})

    # fi there are at least2 ratings, and the ratings have both raters saying yes, we save
    if len(ratings) >= 2 and len(set(ratings.values())) == 1 and ('y' in set(ratings.values())) :
        agreements.append((fname, ratings, data.get("title", ""), data.get("body", ""), data.get("url", "")))

print(f"Files with both annotators agreeing: {len(agreements)}\n")

sample = random.sample(agreements, min(50, len(agreements)))
print(f"Randomly selected {len(sample)} posts:\n")

output = []
for fname, ratings, title, body, url in sorted(sample):
    outcomes = ", ".join(f"{reviewer}: {vote}" for reviewer, vote in ratings.items())
    print(f"{fname}  →  {outcomes}")
    output.append({
        "filename": fname,
        "title": title,
        "body": body,
        "url": url,
        "ratings": ratings,
        "j_open_annotation": "",
        "j_comment": ""
    })

out_path = "../shared_posts.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)
print(f"\nSaved {len(output)} entries to {out_path}")