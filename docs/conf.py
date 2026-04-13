"""Configuration for the Sphinx documentation builder."""

from pathlib import Path
from typing import Any

from sphinx.application import Sphinx
from sphinx.ext import apidoc

project = "Electricity Info NZ"
copyright = "2026, Daniel M"
author = "Daniel M"
release = "0.1.0"

extensions = [
    "myst_parser",
    "sphinx.ext.napoleon",
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
]
napoleon_google_docstring = False

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

templates_path = [
    "_templates",
]

exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
]

html_theme = "furo"
html_static_path = ["_static"]


def run_apidoc(_: Any) -> None:
    """Generate API reference pages automatically."""
    docs_path = Path(__file__).parent
    module_path = docs_path.parent / "src" / "electricityinfo_nz"

    apidoc.main(
        [
            "--force",
            "--module-first",
            "--no-toc",
            "-o",
            docs_path.as_posix(),
            module_path.as_posix(),
        ]
    )


def setup(app: Sphinx) -> None:
    """Register Sphinx build hooks."""
    app.connect("builder-inited", run_apidoc)
