"""Compatibility entry point for the current visible-control browser regression.

The revamp suite replaces the old HTML-grid/modal checks. Existing --url and
--browser arguments are passed through unchanged.
"""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name('playtest_revamp.py')), run_name='__main__')
