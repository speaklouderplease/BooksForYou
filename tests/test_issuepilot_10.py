import os
import unittest
from unittest.mock import patch

from booksforyou.app import format_book


class FormatBookWrappingTests(unittest.TestCase):
    def test_long_title_and_author_list_wrap_with_aligned_values(self):
        title = "The Remarkable Adventures of a Traveller Across the World"
        authors = ["Alexandra Hamilton", "Benjamin Fitzgerald", "Catherine Montgomery"]
        book = {"id": 1, "title": title, "authors": [{"name": name} for name in authors]}
        with patch.dict(os.environ, {"COLUMNS": "48", "LINES": "24"}):
            lines = format_book(book).splitlines()

        author_start = next(i for i, line in enumerate(lines) if line.startswith("Author: "))
        for field, label, value in (
            (lines[:author_start], "Title:  ", title),
            (lines[author_start:-1], "Author: ", "; ".join(authors)),
        ):
            with self.subTest(label=label):
                self.assertGreater(len(field), 1)
                self.assertTrue(field[0].startswith(label))
                for line in field[1:]:
                    self.assertEqual(len(line) - len(line.lstrip()), 8)
                self.assertLessEqual(max(map(len, field)), 48)
                self.assertEqual(" ".join(line[8:] for line in field), value)
        self.assertEqual(lines[-1], "Link:   https://www.gutenberg.org/ebooks/1")
