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
        agreements.append((fname, ratings))

print(f"Files with both annotators agreeing: {len(agreements)}\n")

sample = random.sample(agreements, min(50, len(agreements)))
print(f"Randomly selected {len(sample)} posts:\n")
for fname, ratings in sorted(sample):
    outcomes = ", ".join(f"{reviewer}: {vote}" for reviewer, vote in ratings.items())
    print(f"{fname}  →  {outcomes}")