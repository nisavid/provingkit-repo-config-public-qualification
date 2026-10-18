# Repository configuration public qualification fixture

This generated Python project supplies executable behavior and a separate content contract for Mergecraft's repository-configuration qualification. It contains no production service, deployment credentials, or private source.

Run the catalog renderer from the repository root:

```sh
python -m fixture_catalog plugins/demo/catalog.json
```

The included entry produces `hello: Hello fixture` followed by a newline. Entries render in the order declared in the catalog.

Validate the catalog's relationship to its Markdown resources separately:

```sh
python scripts/validate_catalog.py plugins/demo
```

The catalog declares `schema_version: 1` and a `resources` array. Each resource has nonempty `id`, `title`, and `file` strings. IDs are unique, and each file refers to an existing `.md` resource with a first ATX heading matching its title and nonempty raw content after that heading. CommonMark block parsing distinguishes real hash-prefixed headings, such as `# Hello fixture`, from text inside code fences, HTML comments, and raw HTML blocks. Titles compare the heading's Markdown source text after removing its ATX delimiters, rather than rendered HTML or formatting-stripped text. The validator returns zero on success and a nonzero status with a diagnostic on violation. Code scanning does not establish this content contract.

Use CPython 3.14.6, pinned in `.python-version`. Install the pinned Markdown parser and its dependency before validation or tests:

```sh
python -m pip install --require-hashes --only-binary=:all: -r requirements.txt
```

Run standard-library `unittest` behavioral tests through the real command-line interfaces:

```sh
python -m unittest discover -s tests -v
```

This project is a qualification fixture. Hosted settings, analysis coverage, and merge enforcement require their own observed evidence. The authorized experiment ends by disabling workflows and retaining the repository.

Documentation-only pull requests are part of this fixture's qualification cases. They exercise whether the maintained project checks report on non-code changes.
<!-- Public fixture control: project checks restored. -->
<!-- Public fixture control: current check before omission. -->
