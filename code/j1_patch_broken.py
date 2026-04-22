import json
import os
import subprocess
import sys

RAW_DIR = os.path.join(os.path.dirname(__file__), "../raw")
REQUIRED_FIELDS = {"id", "title", "url", "num_comments"}

invalid_json = []
missing_fields = []

for filename in sorted(os.listdir(RAW_DIR)):
    if not filename.endswith(".json"):
        continue

    filepath = os.path.join(RAW_DIR, filename)

    try:
        with open(filepath) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        invalid_json.append((filename, str(e)))
        continue

    missing = REQUIRED_FIELDS - data.keys()
    if missing:
        subprocess.run(["git", "restore", filepath], check=True)
        missing_fields.append((filename, sorted(missing)))

total_issues = len(invalid_json) + len(missing_fields)

if invalid_json:
    print(f"\n=== Invalid JSON ({len(invalid_json)} files) ===")
    for filename, error in invalid_json:
        print(f"{filename}")

if missing_fields:
    print(f"\n=== Missing required fields ({len(missing_fields)} files) ===")
    for filename, missing in missing_fields:
        print(f"  {filename}: missing {', '.join(missing)}")

if total_issues == 0:
    print("All files are valid and have required fields.")
else:
    print(f"\nTotal files with issues: {total_issues}")

sys.exit(1 if total_issues else 0)
