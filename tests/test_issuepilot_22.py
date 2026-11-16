import contextlib
import io
import runpy
import sys
import unittest
import urllib.error
from unittest import mock


class CommandLineTests(unittest.TestCase):
    def test_help_prints_usage_without_fetching_a_book(self):
        output = io.StringIO()
        with mock.patch.object(sys, "argv", ["booksforyou", "--help"]):
            with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("offline")) as urlopen:
                with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as exit_info:
                    runpy.run_module("booksforyou.__main__", run_name="__main__")

        self.assertIn("usage: booksforyou", output.getvalue())
        self.assertEqual(exit_info.exception.code, 0)
        urlopen.assert_not_called()
