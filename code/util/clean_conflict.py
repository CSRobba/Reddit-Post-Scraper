from glob import glob
import os
from pathlib import Path
import re

def resolve_conflict(text):
    # Remove conflict markers, keep HEAD version only
    text = re.sub(
        r'<<<<<<< [^\n]+\n(.*?)=======\n(.*?)>>>>>>> [^\n]+\n',
        r'\1\2',
        text,
        flags=re.DOTALL
    )

    text = text.replace('    "view_count": null\n', '')
    return text

if __name__ == "__main__":
    for path in Path("../../raw/").glob('*.json'):
        text = open(path).read()
        if '<<<<<<<' in text:
            fixed = resolve_conflict(text)
            open(path, 'w').write(fixed)