import io
import random
import unittest
import urllib.error
from unittest import mock

from booksforyou import api, app


def make_book(book_id, title="A Title", authors=None):
    if authors is None:
        authors = [{"name": "Austen, Jane", "birth_year": 1775, "death_year": 1817}]
    return {"id": book_id, "title": title, "authors": authors}


class FormatBookTests(unittest.TestCase):
    def test_full_record(self):
        text = app.format_book(make_book(1342, "Pride and Prejudice"))
        self.assertIn("Title:  Pride and Prejudice", text)
        self.assertIn("Author: Jane Austen (1775-1817)", text)
        self.assertIn("https://www.gutenberg.org/ebooks/1342", text)

    def test_no_authors(self):
        text = app.format_book(make_book(5, authors=[]))
        self.assertIn("Author: Unknown author", text)

    def test_missing_years(self):
        authors = [{"name": "Anonymous", "birth_year": None, "death_year": None}]
        self.assertIn("Author: Anonymous", app.format_book(make_book(2, authors=authors)))

    def test_only_birth_year(self):
        authors = [{"name": "Doe, John", "birth_year": 1900, "death_year": None}]
        self.assertIn("John Doe (born 1900)", app.format_book(make_book(3, authors=authors)))

    def test_missing_title(self):
        book = {"id": 9, "authors": []}
        self.assertIn("Title:  Untitled", app.format_book(book))


class RandomBookTests(unittest.TestCase):
    def test_returns_book_from_chosen_position(self):
        first = {"count": 64, "results": [make_book(i) for i in range(32)]}
        second = {"count": 64, "results": [make_book(100 + i) for i in range(32)]}
        pages = {1: first, 2: second}
        with mock.patch.object(api, "fetch_page", side_effect=lambda p: pages[p]):
            # index 35 -> page 2, position 3
            rng = mock.Mock()
            rng.randrange.return_value = 35
            book = api.random_book(rng=rng)
        self.assertEqual(book["id"], 103)

    def test_retries_when_index_falls_past_short_last_page(self):
        # Page 2 only holds 8 books, so index 40 (page 2, position 8) is out of range.
        first = {"count": 64, "results": [make_book(i) for i in range(32)]}
        last = {"count": 64, "results": [make_book(200 + i) for i in range(8)]}
        pages = {1: first, 2: last}
        rng = mock.Mock()
        rng.randrange.side_effect = [40, 33]  # first draw is out of range, second is valid
        with mock.patch.object(api, "fetch_page", side_effect=lambda p: pages[p]):
            book = api.random_book(rng=rng)
        self.assertEqual(book["id"], 201)
        self.assertEqual(rng.randrange.call_count, 2)

    def test_picks_only_from_popular_pages(self):
        first = {"count": 79767, "results": [make_book(i) for i in range(32)]}
        rng = mock.Mock()
        rng.randrange.return_value = 0
        with mock.patch.object(api, "fetch_page", return_value=first):
            api.random_book(rng=rng)
        rng.randrange.assert_called_once_with(api.POPULAR_PAGES * api.PAGE_SIZE)

    def test_empty_catalogue_raises(self):
        with mock.patch.object(api, "fetch_page", return_value={"count": 0, "results": []}):
            with self.assertRaises(api.CatalogueError):
                api.random_book(rng=random.Random(0))


class NetworkErrorTests(unittest.TestCase):
    def test_network_failure_becomes_catalogue_error(self):
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("offline")):
            with self.assertRaises(api.CatalogueError):
                api.fetch_page(1)


class RunLoopTests(unittest.TestCase):
    def test_enter_then_quit_shows_two_books(self):
        books = iter([make_book(1, "First"), make_book(2, "Second")])
        answers = iter(["", "q"])
        out = []
        code = app.run(
            input_func=lambda _prompt: next(answers),
            output=out.append,
            picker=lambda: next(books),
        )
        self.assertEqual(code, 0)
        joined = "\n".join(out)
        self.assertIn("Title:  First", joined)
        self.assertIn("Title:  Second", joined)
        self.assertIn("Happy reading!", joined)

    def test_catalogue_error_exits_with_failure(self):
        def broken():
            raise api.CatalogueError("offline")

        out = []
        code = app.run(input_func=lambda _p: "", output=out.append, picker=broken)
        self.assertEqual(code, 1)
        self.assertTrue(any("Sorry" in line for line in out))

    def test_end_of_input_quits_cleanly(self):
        def raise_eof(_prompt):
            raise EOFError

        code = app.run(input_func=raise_eof, output=lambda _l: None,
                       picker=lambda: make_book(1))
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
