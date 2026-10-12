"""Observe the generated project's public command-line behavior."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CatalogRenderingTests(unittest.TestCase):
    def test_catalog_entry_is_rendered_with_its_title(self):
        with tempfile.TemporaryDirectory() as directory:
            catalog = Path(directory) / "catalog.json"
            catalog.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "resources": [
                            {
                                "id": "hello",
                                "title": "Hello fixture",
                                "file": "resources/hello.md",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "-B", "-m", "fixture_catalog", str(catalog)],
                cwd=ROOT,
                env={"PATH": os.defpath, "LANG": "C.UTF-8"},
                capture_output=True,
                text=True,
                timeout=20,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "hello: Hello fixture\n")

    def test_resources_are_rendered_in_catalog_order(self):
        with tempfile.TemporaryDirectory() as directory:
            catalog = Path(directory) / "catalog.json"
            catalog.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "resources": [
                            {"id": "zebra", "title": "Last alphabetically", "file": "zebra.md"},
                            {"id": "alpha", "title": "First alphabetically", "file": "alpha.md"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "-B", "-m", "fixture_catalog", str(catalog)],
                cwd=ROOT,
                env={"PATH": os.defpath, "LANG": "C.UTF-8"},
                capture_output=True,
                text=True,
                timeout=20,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "zebra: Last alphabetically\nalpha: First alphabetically\n")


class CatalogValidationTests(unittest.TestCase):
    def run_validator(self, catalog, resource_files=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            if resource_files is None:
                resource_files = {"resources/hello.md": "# Hello fixture\n\nA generated resource.\n"}
            for name, content in resource_files.items():
                resource = root / name
                resource.parent.mkdir(parents=True, exist_ok=True)
                resource.write_text(content, encoding="utf-8")
            (root / "catalog.json").write_text(
                json.dumps(catalog), encoding="utf-8"
            )
            return subprocess.run(
                [sys.executable, "-B", "scripts/validate_catalog.py", str(root)],
                cwd=ROOT,
                env={"PATH": os.defpath, "LANG": "C.UTF-8"},
                capture_output=True,
                text=True,
                timeout=20,
            )

    def test_catalog_root_must_be_an_object(self):
        for catalog in ([], None, "catalog", 1, True):
            with self.subTest(catalog=catalog):
                result = self.run_validator(catalog)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("catalog must be an object", result.stderr.lower())

    def test_unsupported_catalog_schema_is_rejected(self):
        for version in (2, True, 1.0):
            with self.subTest(version=version, type=type(version).__name__):
                result = self.run_validator({"schema_version": version, "resources": []})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("schema_version", result.stderr)

    def test_catalog_requires_complete_resource_records(self):
        cases = [
            ({"schema_version": 1}, "resources"),
            ({"schema_version": 1, "resources": "hello"}, "resources"),
            ({"schema_version": 1, "resources": ["hello"]}, "resource"),
            ({"schema_version": 1, "resources": [{}]}, "id"),
            ({"schema_version": 1, "resources": [{"id": "hello"}]}, "title"),
            (
                {"schema_version": 1, "resources": [{"id": "hello", "title": "Hello fixture"}]},
                "file",
            ),
            (
                {"schema_version": 1, "resources": [{"id": "", "title": "Hello fixture", "file": "resources/hello.md"}]},
                "id",
            ),
        ]
        for catalog, diagnostic in cases:
            with self.subTest(catalog=catalog):
                result = self.run_validator(catalog)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(diagnostic, result.stderr)

    def test_generated_project_is_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "resources").mkdir()
            (root / "resources/hello.md").write_text(
                "# Hello fixture\n\nA generated resource.\n", encoding="utf-8"
            )
            (root / "catalog.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "resources": [
                            {
                                "id": "hello",
                                "title": "Hello fixture",
                                "file": "resources/hello.md",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "-B", "scripts/validate_catalog.py", str(root)],
                cwd=ROOT,
                env={"PATH": os.defpath, "LANG": "C.UTF-8"},
                capture_output=True,
                text=True,
                timeout=20,
            )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_duplicate_resource_ids_are_rejected(self):
        result = self.run_validator(
            {
                "schema_version": 1,
                "resources": [
                    {"id": "hello", "title": "Hello fixture", "file": "resources/hello.md"},
                    {"id": "hello", "title": "Hello fixture", "file": "resources/hello.md"},
                ],
            }
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Duplicate resource id: hello", result.stderr)

    def test_resources_must_reference_existing_markdown_files(self):
        cases = [
            ("resources/missing.md", "does not exist"),
            ("resources/hello.txt", "Markdown"),
        ]
        for name, diagnostic in cases:
            with self.subTest(file=name):
                result = self.run_validator(
                    {
                        "schema_version": 1,
                        "resources": [{"id": "hello", "title": "Hello fixture", "file": name}],
                    },
                    {"resources/hello.txt": "# Hello fixture\n\nA generated resource.\n"},
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(diagnostic, result.stderr)

    def test_resource_heading_must_match_its_catalog_title(self):
        for content in ("# Wrong title\n\nA body.\n", "A body without a heading.\n"):
            with self.subTest(content=content):
                result = self.run_validator(
                    {
                        "schema_version": 1,
                        "resources": [{"id": "hello", "title": "Hello fixture", "file": "resources/hello.md"}],
                    },
                    {"resources/hello.md": content},
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("heading", result.stderr)
                self.assertIn("Hello fixture", result.stderr)

    def test_headings_inside_code_fences_do_not_select_the_resource_title(self):
        fences = [
            ("```", "```"),
            ("~~~python", "~~~"),
            ("   ````text", "   `````   "),
        ]
        for opening, closing in fences:
            for suffix, accepted in (
                ("# Wrong title\n\nA body.\n", False),
                ("A body with no actual heading.\n", False),
                ("# Hello fixture\n\nA body.\n", True),
            ):
                with self.subTest(opening=opening, suffix=suffix):
                    result = self.run_validator(
                        {
                            "schema_version": 1,
                            "resources": [{"id": "hello", "title": "Hello fixture", "file": "resources/hello.md"}],
                        },
                        {"resources/hello.md": f"{opening}\n# Hello fixture\n{closing}\n{suffix}"},
                    )
                    if accepted:
                        self.assertEqual(result.returncode, 0, result.stderr)
                    else:
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn("heading", result.stderr)

    def test_first_atx_heading_allows_at_most_three_leading_spaces(self):
        for spaces in (1, 2, 3, 4):
            for title in ("Hello fixture", "Wrong title"):
                with self.subTest(spaces=spaces, title=title):
                    content = f"{' ' * spaces}# {title}\n\nA body.\n"
                    if title == "Wrong title":
                        content += "# Hello fixture\n\nA later body.\n"
                    result = self.run_validator(
                        {
                            "schema_version": 1,
                            "resources": [{"id": "hello", "title": "Hello fixture", "file": "resources/hello.md"}],
                        },
                        {"resources/hello.md": content},
                    )
                    accepted = (spaces <= 3 and title == "Hello fixture") or (
                        spaces == 4 and title == "Wrong title"
                    )
                    if accepted:
                        self.assertEqual(result.returncode, 0, result.stderr)
                    else:
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn("heading", result.stderr)

    def test_empty_first_atx_heading_is_not_replaced_by_a_later_title(self):
        cases = [
            ("#", False),
            ("##   ", False),
            ("###\t", False),
            ("#### ###", False),
            ("###### \t## \t", False),
            ("# Hello fixture ### ", True),
            ("######\tHello fixture\t##\t", True),
        ]
        for spaces in (0, 1, 2, 3):
            for first_heading, accepted in cases:
                with self.subTest(spaces=spaces, first_heading=first_heading):
                    result = self.run_validator(
                        {
                            "schema_version": 1,
                            "resources": [{"id": "hello", "title": "Hello fixture", "file": "resources/hello.md"}],
                        },
                        {"resources/hello.md": f"{' ' * spaces}{first_heading}\n\n# Hello fixture\n\nA body.\n"},
                    )
                    if accepted:
                        self.assertEqual(result.returncode, 0, result.stderr)
                    else:
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn("heading", result.stderr)
                        self.assertIn("Hello fixture", result.stderr)

    def test_html_comment_headings_do_not_select_the_resource_title(self):
        cases = [
            ("<!--\n# Hello fixture\n-->\n# Wrong title\n\nA body.\n", False),
            ("<!--\n# Hello fixture\n-->\nNo actual heading.\n", False),
            ("<!--\n# Wrong title\n-->\n# Hello fixture\n\nA body.\n", True),
            ("<!--\n```\n# Hello fixture\n-->\n# Hello fixture\n\nA body.\n", True),
            ("```\n<!--\n```\n# Hello fixture\n\nA body.\n", True),
            ("<!--\n# Hello fixture\nAn unclosed comment.\n", False),
            ("<!-- hidden heading -->\n# Hello fixture\n\nA body.\n", True),
        ]
        for spaces in (0, 1, 2, 3):
            for content, accepted in cases:
                with self.subTest(spaces=spaces, content=content):
                    result = self.run_validator(
                        {
                            "schema_version": 1,
                            "resources": [{"id": "hello", "title": "Hello fixture", "file": "resources/hello.md"}],
                        },
                        {"resources/hello.md": " " * spaces + content},
                    )
                    if accepted:
                        self.assertEqual(result.returncode, 0, result.stderr)
                    else:
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn("heading", result.stderr)
                        self.assertIn("Hello fixture", result.stderr)

    def test_raw_html_block_headings_do_not_select_the_resource_title(self):
        blocks = [
            "<script>\n# Hello fixture\n</script>\n",
            "<?fixture\n# Hello fixture\n?>\n",
            "<!DOCTYPE\n# Hello fixture\n>\n",
            "<![CDATA[\n# Hello fixture\n]]>\n",
            "<div>\n# Hello fixture\n</div>\n\n",
            "   <fixture-box>\n# Hello fixture\n</fixture-box>\n\n",
        ]
        for block in blocks:
            for suffix, accepted in (
                ("# Wrong title\n\nA body.\n", False),
                ("No actual heading.\n", False),
                ("# Hello fixture\n\nA body.\n", True),
            ):
                with self.subTest(block=block, suffix=suffix):
                    result = self.run_validator(
                        {
                            "schema_version": 1,
                            "resources": [{"id": "hello", "title": "Hello fixture", "file": "resources/hello.md"}],
                        },
                        {"resources/hello.md": block + suffix},
                    )
                    if accepted:
                        self.assertEqual(result.returncode, 0, result.stderr)
                    else:
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn("heading", result.stderr)
                        self.assertIn("Hello fixture", result.stderr)

    def test_resource_must_have_content_after_its_heading(self):
        result = self.run_validator(
            {
                "schema_version": 1,
                "resources": [{"id": "hello", "title": "Hello fixture", "file": "resources/hello.md"}],
            },
            {"resources/hello.md": "# Hello fixture\n\n \t\n"},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("body", result.stderr)


if __name__ == "__main__":
    unittest.main()
