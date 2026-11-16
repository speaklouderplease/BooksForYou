import unittest

from booksforyou.app import format_book


class AuthorDatesTests(unittest.TestCase):
    def test_book_explains_the_author_years(self):
        book = {
            "id": 1342,
            "title": "Pride and Prejudice",
            "authors": [{"name": "Austen, Jane", "birth_year": 1775, "death_year": 1817}],
        }
        lines = format_book(book).splitlines()
        self.assertIn("Author: Jane Austen (1775-1817)", lines)
        self.assertIn("Years on the Author line indicate birth and death dates.", lines)
