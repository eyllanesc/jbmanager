"""Sphinx configuration."""
project = "JBManager"
author = "Edwin Yllanes"
copyright = "2023, Edwin Yllanes"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_click",
    "myst_parser",
]
autodoc_typehints = "description"
html_theme = "furo"
