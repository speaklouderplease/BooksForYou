import random
import unittest
from unittest import mock

from booksforyou import api


class CatalogueExhaustionTests(unittest.TestCase):
    def test_cached_unusable_positions_do_not_prevent_exhaustion(self):
        cases = [
            ({"count": 2, "results": [None, {"id": 1}]}, 0),
            ({"count": 2, "results": [{"id": 1}]}, 1),
            ({"count": 2, "results": [None, {"title": "No identifier"}]}, 0),
        ]
        for page, seed in cases:
            with self.subTest(page=page):
                with mock.patch.object(api, "fetch_page", return_value=page):
                    catalogue = api.Catalogue(rng=random.Random(seed))
                    self.assertIsInstance(catalogue.random_book(), dict)
                    try:
                        with self.assertRaises(api.CatalogueExhausted):
                            catalogue.random_book()
                    except api.CatalogueError as exc:
                        self.fail(f"All valid picks were returned, but exhaustion raised {exc!r}")

    def test_an_entirely_unusable_catalogue_is_still_an_error(self):
        page = {"count": 1, "results": [None]}
        with mock.patch.object(api, "fetch_page", return_value=page):
            catalogue = api.Catalogue(rng=random.Random(0))
            with self.assertRaises(api.CatalogueError):
                catalogue.random_book()
            with self.assertRaises(api.CatalogueError):
                catalogue.random_book()

    def test_failed_page_fetch_does_not_consume_its_position(self):
        class LastPosition:
            def randrange(self, stop):
                return stop - 1

        first = {"count": api.PAGE_SIZE + 1, "results": [{"id": n} for n in range(api.PAGE_SIZE)]}
        last = {"count": api.PAGE_SIZE + 1, "results": [{"id": 1000}]}
        error = api.CatalogueError(api.NETWORK_ERROR, api.CONNECTION_HINT)
        with mock.patch.object(api, "fetch_page", side_effect=[first, error, last]) as fetch:
            catalogue = api.Catalogue(rng=LastPosition())
            with self.assertRaises(api.CatalogueError):
                catalogue.random_book()
            self.assertEqual(catalogue.random_book(), {"id": 1000})
            self.assertEqual(fetch.call_args_list, [mock.call(1), mock.call(2), mock.call(2)])

    def test_unfetched_pages_remain_available_after_unusable_draws(self):
        class FirstThenBadPosition:
            def __init__(self):
                self.calls = 0

            def randrange(self, stop):
                self.calls += 1
                return 0 if self.calls == 1 or stop == 1 else 1

        first = {"count": api.PAGE_SIZE + 1, "results": [{"id": 1}]}
        last = {"count": api.PAGE_SIZE + 1, "results": [{"id": 2}]}
        with mock.patch.object(api, "fetch_page", side_effect=[first, last]) as fetch:
            catalogue = api.Catalogue(rng=FirstThenBadPosition())
            self.assertEqual(catalogue.random_book(), {"id": 1})
            with self.assertRaises(api.CatalogueError):
                catalogue.random_book()
            self.assertEqual(catalogue.random_book(), {"id": 2})
            self.assertEqual(fetch.call_args_list, [mock.call(1), mock.call(2)])
