import unittest

from booksforyou.app import format_book


class FormatAuthorTests(unittest.TestCase):
    def test_names_with_multiple_commas_keep_catalogue_order(self):
        for name in ("Dumas, Alexandre, père", "Smith, John, Sir"):
            with self.subTest(name=name):
                book = {"authors": [{"name": name}]}
                self.assertIn(f"Author: {name}", format_book(book).splitlines())
