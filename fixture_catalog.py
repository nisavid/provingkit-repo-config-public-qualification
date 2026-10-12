"""Render the generated resource catalog."""

import json
from pathlib import Path
import sys


def main():
    catalog = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    for entry in catalog["resources"]:
        print(f"{entry['id']}: {entry['title']}")


if __name__ == "__main__":
    main()
