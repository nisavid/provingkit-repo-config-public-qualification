"""Validate the generated plugin's catalog and resources."""

import json
from pathlib import Path
import sys

from markdown_it import MarkdownIt


def main():
    root = Path(sys.argv[1])
    catalog = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
    if not isinstance(catalog, dict):
        print("Catalog must be an object.", file=sys.stderr)
        return 1
    version = catalog.get("schema_version")
    if type(version) is not int or version != 1:
        print("schema_version must be 1.", file=sys.stderr)
        return 1
    if not isinstance(catalog.get("resources"), list):
        print("resources must be an array.", file=sys.stderr)
        return 1
    ids = set()
    markdown = MarkdownIt("commonmark")
    for entry in catalog["resources"]:
        if not isinstance(entry, dict):
            print("Each resource must be an object.", file=sys.stderr)
            return 1
        for field in ("id", "title", "file"):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                print(f"Resource {field} must be a nonempty string.", file=sys.stderr)
                return 1
        if entry["id"] in ids:
            print(f"Duplicate resource id: {entry['id']}", file=sys.stderr)
            return 1
        ids.add(entry["id"])
        resource = root / entry["file"]
        if resource.suffix != ".md":
            print(f"Resource file must be Markdown: {entry['file']}", file=sys.stderr)
            return 1
        if not resource.is_file():
            print(f"Resource file does not exist: {entry['file']}", file=sys.stderr)
            return 1
        source = resource.read_text(encoding="utf-8")
        heading = None
        body_start = None
        tokens = markdown.parse(source)
        for index, token in enumerate(tokens):
            if token.type == "heading_open" and token.markup.startswith("#"):
                heading = tokens[index + 1].content
                body_start = token.map[1]
                break
        if heading != entry["title"]:
            print(f"Resource heading must match title: {entry['title']}", file=sys.stderr)
            return 1
        if not "\n".join(source.split("\n")[body_start:]).strip():
            print(f"Resource body must be nonempty: {entry['file']}", file=sys.stderr)
            return 1
    print("Catalog is valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
