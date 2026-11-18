import random
import unittest
from unittest import mock

from booksforyou import api, app


class RecommendationTests(unittest.TestCase):
    def test_session_shows_each_book_once(self):
        page = {
            "count": 2,
            "results": [{"id": 1, "title": "First"}, {"id": 2, "title": "Second"}],
        }
        answers = iter(["", "", "q"])
        output = []
        # With replacement, this seed selects the second position twice in a row.
        with mock.patch.object(api, "fetch_page", return_value=page):
            with mock.patch.object(api, "random", random.Random(0)):
                code = app.run(input_func=lambda _prompt: next(answers), output=output.append)

        titles = [line for line in "\n".join(output).splitlines() if line.startswith("Title:")]
        self.assertCountEqual(titles, ["Title:  First", "Title:  Second"])
        self.assertIn("You've seen all available picks.", output)
        self.assertEqual(code, 0)
