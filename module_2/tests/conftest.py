# module_2/tests/conftest.py
import sys, pathlib

# Add the parent directory (module_2/) to sys.path so `import scrape` works
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
