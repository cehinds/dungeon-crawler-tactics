from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from run_ci_browser_check import run


class BrowserDiagnosticsTests(unittest.TestCase):
    def test_success_keeps_zero_exit_and_does_not_annotate(self):
        output = io.StringIO()
        with redirect_stdout(output):
            result = run('success', [sys.executable, '-c', "print('passed')"])
        self.assertEqual(result, 0)
        self.assertNotIn('::error', output.getvalue())

    def test_failure_preserves_exit_and_publishes_bounded_escaped_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = Path(tmp) / 'summary.md'
            output = io.StringIO()
            command = [sys.executable, '-c', "import sys;print('x'*10000);print('failure 50% <cause>');sys.exit(3)"]
            with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': str(summary)}), redirect_stdout(output):
                result = run('fixture', command)
            self.assertEqual(result, 3)
            annotation = output.getvalue().split('::error title=fixture::')[1]
            self.assertIn('50%25', annotation)
            self.assertIn('%0A', annotation)
            self.assertLess(len(annotation), 6100)
            self.assertIn('failure 50% &lt;cause&gt;', summary.read_text())
            self.assertLess(len(summary.read_text()), 6500)
