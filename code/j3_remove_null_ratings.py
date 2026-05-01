import json
import glob
import os

# Set up paths
raw_dir = os.path.join(os.path.dirname(__file__), "..", "raw")
files = glob.glob(os.path.join(raw_dir, "*.json"))

modified_count = 0

for path in files:
    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            continue  # Skip files that aren't valid JSON

    # Logic to target the specific field
    rr = data.get("relevance_rate")
    
    # Check if the field is a dict and contains the "null" key
    if isinstance(rr, dict) and "null" in rr:
        del rr["null"]  # Remove the field in memory
        
        # Overwrite the original file with the modified data
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        
        modified_count += 1

print(f"Update complete. Modified {modified_count} files.")