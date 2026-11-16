import io
import runpy
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch


class RedirectedOutputTests(unittest.TestCase):
    def test_cli_prints_non_latin_title_to_cp1252_stdout(self):
        title = "War and Peace — Война и мир 戦争と平和"
        book = {"id": 2600, "title": title}
        with io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict") as stdout:
            with redirect_stdout(stdout), patch("sys.stdin", io.StringIO("q\n")), patch(
                "booksforyou.api.fetch_page", return_value={"count": 1, "results": [book]}
            ):
                try:
                    with self.assertRaises(SystemExit) as exit_info:
                        runpy.run_module("booksforyou", run_name="__main__")
                except UnicodeEncodeError as exc:
                    self.fail(f"Printing the recommendation raised {exc}")

            self.assertEqual(exit_info.exception.code, 0)
            stdout.seek(0)
            output = stdout.read()
            self.assertIn("Title:  War and Peace — ????? ? ??? ?????\n", output)
            self.assertIn("Happy reading!", output)
