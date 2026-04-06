import json
import os

RAW_FOLDER = "../raw/"

disagreements = []

for fname in os.listdir(RAW_FOLDER):
    fpath = os.path.join(RAW_FOLDER, fname)
    with open(fpath, encoding="utf-8") as f:
        data = json.load(f)

    ratings = data.get("relevance_rate", {})
    if len(ratings) >= 2 and len(set(ratings.values())) > 1:
        disagreements.append((fname, ratings))

print(f"Files with disagreements: {len(disagreements)}\n")
for fname, ratings in sorted(disagreements):
    outcomes = ", ".join(f"{reviewer}: {vote}" for reviewer, vote in ratings.items())
    print(f"{fname}  →  {outcomes}")
