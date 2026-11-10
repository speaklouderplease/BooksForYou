"""Access to the Gutendex catalogue of public-domain books (https://gutendex.com)."""

import json
import math
import random
import urllib.error
import urllib.request

API_URL = "https://gutendex.com/books/"
PAGE_SIZE = 32  # Gutendex returns 32 books per page.
# Gutendex lists books by download count, most popular first. Deep pages are very slow
# to serve, so we only pick from the first POPULAR_PAGES pages (320 most-downloaded books).
POPULAR_PAGES = 10
TIMEOUT_SECONDS = 15
USER_AGENT = "BooksForYou/1.0"


class CatalogueError(Exception):
    """Raised when the book catalogue cannot be reached or returns unusable data."""


def _get_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise CatalogueError(f"the book catalogue could not be reached ({exc}).") from exc


def fetch_page(page):
    """Return one page of the catalogue as a dict with 'count' and 'results'."""
    return _get_json(f"{API_URL}?page={page}")


def random_book(rng=random):
    """Pick a book uniformly at random from the most popular books in the catalogue."""
    first = fetch_page(1)
    count = first.get("count", 0)
    if not isinstance(count, int) or count <= 0:
        raise CatalogueError("the book catalogue is empty.")

    pool = min(count, POPULAR_PAGES * PAGE_SIZE)
    while True:
        index = rng.randrange(pool)
        page_number, position = divmod(index, PAGE_SIZE)
        page_number += 1  # Gutendex pages start at 1.
        data = first if page_number == 1 else fetch_page(page_number)
        results = data.get("results") or []
        # The last page can be shorter than PAGE_SIZE; retry if the index falls outside it.
        if position < len(results):
            return results[position]
