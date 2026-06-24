"""Ensure the `apex` package is importable when running tests.

pytest imports the rootdir conftest first and inserts its directory into
sys.path, so plain `pytest` (not just `python -m pytest`) resolves `import apex`
without an editable install. Keeps CI and local runs identical.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
