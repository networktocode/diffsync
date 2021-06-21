# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

try:
    import toml
except ImportError:
    sys.exit("Please make sure to `pip install toml` or enable the Poetry shell and run `poetry install`.")


# -- Variable setup --------------------------------------------------------------

PYPROJECT_CONFIG = toml.load(f"{os.path.dirname(os.path.dirname(os.getcwd()))}/pyproject.toml")
TOOL_CONFIG = PYPROJECT_CONFIG["tool"]["poetry"]

# -- Project information -----------------------------------------------------

project = TOOL_CONFIG["name"]
copyright = f"2021, {','.join(TOOL_CONFIG['authors'])}"
author = ','.join(TOOL_CONFIG['authors'])

# The full version, including alpha/beta/rc tags
release = TOOL_CONFIG["version"]


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "m2r2"
]

autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
    "special-members": "__init__",
    "undoc-members": True,
}


# Add any paths that contain templates here, relative to this directory.
templates_path = ['templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['static']


def remove_module_docstring(app, what, name, obj, options, lines):
    """Removes copyright information at the top of each module to prevent unneeded reference in the API documentation"""
    if what == "module":
        # At the module level, remove everything except the first line containing a summary of the module. All
        # lines that follow are copyright notices.
        del lines[1:]


def setup(app):
    app.connect("autodoc-process-docstring", remove_module_docstring)
