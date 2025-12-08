"""Generate code reference pages."""

from pathlib import Path

import mkdocs_gen_files

# Base path to the diffsync package
# When mkdocs runs this script, it runs from the project root
# So we need to reference the diffsync package relative to the project root
base_path = Path("diffsync")

# Directories to exclude from code reference generation
exclude_dirs = {"__pycache__", "static", "tests", "examples", "docs"}

for file_path in base_path.rglob("*.py"):
    # Skip files in excluded directories
    if any(part in exclude_dirs for part in file_path.parts):
        continue

    # Ensure the file is actually within the base_path directory
    try:
        file_path.relative_to(base_path)
    except ValueError:
        continue

    module_path = file_path.with_suffix("")
    doc_path = file_path.with_suffix(".md")
    full_doc_path = Path("code-reference", doc_path)

    parts = list(module_path.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        IDENTIFIER = ".".join(parts)  # pylint: disable=invalid-name
        print(f"::: {IDENTIFIER}", file=fd)

    mkdocs_gen_files.set_edit_path(full_doc_path, file_path)
