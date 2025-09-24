# docs/source/conf.py

# --- Make 'src' importable for autodoc ---------------------------------------
import os, sys
sys.path.insert(0, os.path.abspath('../..'))

# --- Project information ------------------------------------------------------
project = 'Grad Café Analytics — Module 4'
author = 'Gabriel Bisco Reinato'
release = '0.1.0'
language = 'en'

# --- General configuration ----------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
]

# Default autodoc options (explicit :members: used in .rst as well)
autodoc_default_options = {
    'members': True,
}

templates_path = ['_templates']
exclude_patterns = []

autodoc_mock_imports = ['psycopg', 'psycopg2']

# --- HTML output --------------------------------------------------------------
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static'] 
