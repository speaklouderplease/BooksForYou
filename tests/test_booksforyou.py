import http.client
import random
import unittest
import urllib.error
from unittest import mock

from booksforyou import api, app


def make_book(book_id, title="A Title", authors=None):
    if authors is None:
        authors = [{"name": "Austen, Jane", "birth_year": 1775, "death_year": 1817}]
    return {"id": book_id, "title": title, "authors": authors}


class FakeResponse:
    """Stands in for the object returned by urlopen."""

    def __init__(self, chunks):
        self._chunks = list(chunks)

    def read(self, _size=-1):
        if not self._chunks:
            return b""
        return self._chunks.pop(0)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


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

    def test_null_author_entry_does_not_crash(self):
        text = app.format_book(make_book(1, authors=[None, {"name": "Doe, John"}]))
        self.assertIn("Author: John Doe", text)

    def test_missing_id_shows_unavailable_not_none(self):
        text = app.format_book({"id": None, "title": "X", "authors": []})
        self.assertIn("Read:   unavailable", text)
        self.assertNotIn("None", text)

    def test_control_characters_are_removed_from_remote_text(self):
        book = make_book(4, title="\x1b]0;evil\x07Title")
        text = app.format_book(book)
        self.assertNotIn("\x1b", text)
        self.assertNotIn("\x07", text)
        self.assertIn("Title:  ]0;evil Title", text)

    def test_non_integer_years_are_ignored(self):
        authors = [{"name": "Doe, John", "birth_year": "\x1b1900", "death_year": True}]
        text = app.format_book(make_book(6, authors=authors))
        self.assertIn("Author: John Doe", text)
        self.assertNotIn("1900", text)


class CatalogueTests(unittest.TestCase):
    def test_returns_book_from_chosen_position(self):
        first = {"count": 64, "results": [make_book(i) for i in range(32)]}
        second = {"count": 64, "results": [make_book(100 + i) for i in range(32)]}
        pages = {1: first, 2: second}
        rng = mock.Mock()
        rng.randrange.return_value = 35  # page 2, position 3
        with mock.patch.object(api, "fetch_page", side_effect=lambda p: pages[p]):
            book = api.Catalogue(rng=rng).random_book()
        self.assertEqual(book["id"], 103)

    def test_retries_when_index_falls_past_short_last_page(self):
        # Page 2 only holds 8 books, so index 40 (page 2, position 8) is out of range.
        first = {"count": 64, "results": [make_book(i) for i in range(32)]}
        last = {"count": 64, "results": [make_book(200 + i) for i in range(8)]}
        pages = {1: first, 2: last}
        rng = mock.Mock()
        rng.randrange.side_effect = [40, 33]
        with mock.patch.object(api, "fetch_page", side_effect=lambda p: pages[p]):
            book = api.Catalogue(rng=rng).random_book()
        self.assertEqual(book["id"], 201)
        self.assertEqual(rng.randrange.call_count, 2)

    def test_picks_only_from_popular_pages(self):
        first = {"count": 79767, "results": [make_book(i) for i in range(32)]}
        rng = mock.Mock()
        rng.randrange.return_value = 0
        with mock.patch.object(api, "fetch_page", return_value=first):
            api.Catalogue(rng=rng).random_book()
        rng.randrange.assert_called_once_with(api.POPULAR_PAGES * api.PAGE_SIZE)

    def test_empty_catalogue_raises(self):
        with mock.patch.object(api, "fetch_page", return_value={"count": 0, "results": []}):
            with self.assertRaises(api.CatalogueError) as ctx:
                api.Catalogue(rng=random.Random(0)).random_book()
        self.assertEqual(ctx.exception.message, api.EMPTY_CATALOGUE)

    def test_positive_count_but_empty_first_page_raises_instead_of_hanging(self):
        with mock.patch.object(api, "fetch_page", return_value={"count": 5, "results": []}):
            with self.assertRaises(api.CatalogueError):
                api.Catalogue(rng=random.Random(0)).random_book()

    def test_gives_up_after_max_attempts_and_caches_pages(self):
        # Every draw lands on page 4 at position 4, where Gutendex returns no books.
        empty_page = {"count": 320, "results": []}
        rng = mock.Mock()
        rng.randrange.return_value = 100
        with mock.patch.object(api, "fetch_page", side_effect=[
            {"count": 320, "results": [make_book(1)]},  # page 1
            empty_page,  # page 4, fetched once then cached
        ]) as fetch:
            with self.assertRaises(api.CatalogueError):
                api.Catalogue(rng=rng).random_book()
        self.assertEqual(rng.randrange.call_count, api.MAX_ATTEMPTS)
        self.assertEqual(fetch.call_count, 2)

    def test_non_dict_result_items_are_skipped(self):
        first = {"count": 32, "results": ["junk", make_book(7)]}
        rng = mock.Mock()
        rng.randrange.side_effect = [0, 1]
        with mock.patch.object(api, "fetch_page", return_value=first):
            book = api.Catalogue(rng=rng).random_book()
        self.assertEqual(book["id"], 7)

    def test_non_list_results_is_a_catalogue_error(self):
        with mock.patch.object(api, "fetch_page", return_value={"count": 5, "results": "x"}):
            with self.assertRaises(api.CatalogueError) as ctx:
                api.Catalogue(rng=random.Random(0)).random_book()
        self.assertEqual(ctx.exception.message, api.BAD_REPLY)

    def test_page_one_is_fetched_once_per_session(self):
        first = {"count": 32, "results": [make_book(i) for i in range(32)]}
        catalogue = api.Catalogue(rng=random.Random(0))
        with mock.patch.object(api, "fetch_page", return_value=first) as fetch:
            for _ in range(5):
                catalogue.random_book()
        self.assertEqual(fetch.call_count, 1)


class NetworkErrorTests(unittest.TestCase):
    def test_network_failure_has_connection_hint(self):
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("offline")):
            with self.assertRaises(api.CatalogueError) as ctx:
                api.fetch_page(1)
        self.assertEqual(ctx.exception.message, api.NETWORK_ERROR)
        self.assertEqual(ctx.exception.hint, api.CONNECTION_HINT)

    def test_timeout_is_a_catalogue_error(self):
        with mock.patch("urllib.request.urlopen", side_effect=TimeoutError("slow")):
            with self.assertRaises(api.CatalogueError):
                api.fetch_page(1)

    def test_truncated_body_is_a_catalogue_error(self):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.side_effect = http.client.IncompleteRead(b'{"count"')
        with mock.patch("urllib.request.urlopen", return_value=response):
            with self.assertRaises(api.CatalogueError):
                api.fetch_page(1)

    def test_non_object_json_is_a_catalogue_error(self):
        response = FakeResponse([b"[]"])
        with mock.patch("urllib.request.urlopen", return_value=response):
            with self.assertRaises(api.CatalogueError) as ctx:
                api.fetch_page(1)
        self.assertEqual(ctx.exception.message, api.BAD_REPLY)

    def test_invalid_json_is_a_catalogue_error(self):
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse([b"{nope"])):
            with self.assertRaises(api.CatalogueError):
                api.fetch_page(1)

    def test_oversized_body_is_rejected(self):
        chunk = b"x" * (64 * 1024)
        many = [chunk] * (api.MAX_RESPONSE_BYTES // len(chunk) + 2)
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse(many)):
            with self.assertRaises(api.CatalogueError):
                api.fetch_page(1)

    def test_slow_response_hits_overall_deadline(self):
        clock = iter([0.0, 0.0, api.REQUEST_DEADLINE_SECONDS + 1])
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse([b"{}", b"{}"])):
            with mock.patch.object(api.time, "monotonic", side_effect=lambda: next(clock)):
                with self.assertRaises(api.CatalogueError) as ctx:
                    api.fetch_page(1)
        self.assertEqual(ctx.exception.message, api.TIMEOUT_ERROR)


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

    def test_shows_finding_message_before_each_book(self):
        answers = iter(["q"])
        out = []
        app.run(input_func=lambda _p: next(answers), output=out.append,
                picker=lambda: make_book(1))
        self.assertIn("Finding a book...", out)

    def test_catalogue_error_shows_message_and_hint(self):
        def broken():
            raise api.CatalogueError(api.NETWORK_ERROR, api.CONNECTION_HINT)

        out = []
        code = app.run(input_func=lambda _p: "", output=out.append, picker=broken)
        self.assertEqual(code, 1)
        self.assertIn(
            f"Sorry, {api.NETWORK_ERROR} {api.CONNECTION_HINT}", out
        )

    def test_empty_catalogue_has_no_connection_hint(self):
        def empty():
            raise api.CatalogueError(api.EMPTY_CATALOGUE)

        out = []
        app.run(input_func=lambda _p: "", output=out.append, picker=empty)
        self.assertIn(f"Sorry, {api.EMPTY_CATALOGUE}", out)
        self.assertFalse(any("internet" in line for line in out))

    def test_end_of_input_quits_cleanly(self):
        def raise_eof(_prompt):
            raise EOFError

        code = app.run(input_func=raise_eof, output=lambda _l: None,
                       picker=lambda: make_book(1))
        self.assertEqual(code, 0)

    def test_ctrl_c_during_fetch_exits_cleanly(self):
        def interrupted():
            raise KeyboardInterrupt

        out = []
        code = app.run(input_func=lambda _p: "", output=out.append, picker=interrupted)
        self.assertEqual(code, 0)
        self.assertIn("Happy reading!", out)

    def test_ctrl_c_at_prompt_exits_cleanly(self):
        def interrupted(_prompt):
            raise KeyboardInterrupt

        out = []
        code = app.run(input_func=interrupted, output=out.append,
                       picker=lambda: make_book(1))
        self.assertEqual(code, 0)
        self.assertIn("Happy reading!", out)


if __name__ == "__main__":
    unittest.main()
