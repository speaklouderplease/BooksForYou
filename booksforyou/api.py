"""Access to the Gutendex catalogue of public-domain books (https://gutendex.com)."""

import http.client
import json
import random
import time
import urllib.request

API_URL = "https://gutendex.com/books/"
PAGE_SIZE = 32  # Gutendex returns 32 books per page.
# Gutendex lists books by download count, most popular first. Deep pages are very slow
# to serve, so we only pick from the first POPULAR_PAGES pages (320 most-downloaded books).
POPULAR_PAGES = 10
TIMEOUT_SECONDS = 15  # Applies to each socket operation.
REQUEST_DEADLINE_SECONDS = 20  # Overall budget for reading one response.
MAX_RESPONSE_BYTES = 2 * 1024 * 1024  # A 32-book page is far smaller than this.
MAX_ATTEMPTS = 20  # Draws allowed before giving up on finding a book.
USER_AGENT = "BooksForYou/1.0"

NETWORK_ERROR = "the book catalogue could not be reached."
TIMEOUT_ERROR = "the book catalogue took too long to respond."
BAD_REPLY = "the book catalogue sent a reply that could not be read."
EMPTY_CATALOGUE = "the book catalogue is empty."
NO_BOOK_FOUND = "the book catalogue did not return a book."
CONNECTION_HINT = "Check your internet connection and try again later."
RETRY_HINT = "Please try again later."


class CatalogueError(Exception):
    """Raised when the book catalogue cannot be reached or returns unusable data.

    `message` is a user-facing sentence; `hint` is an optional follow-up sentence.
    Raw exception details are kept on `__cause__` and are not shown to the user.
    """

    def __init__(self, message, hint=None):
        super().__init__(message)
        self.message = message
        self.hint = hint


def _read_limited(response):
    """Read a response body, enforcing a size cap and an overall time budget."""
    deadline = time.monotonic() + REQUEST_DEADLINE_SECONDS
    chunks = []
    total = 0
    while True:
        if time.monotonic() > deadline:
            raise CatalogueError(TIMEOUT_ERROR, CONNECTION_HINT)
        chunk = response.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_RESPONSE_BYTES:
            raise CatalogueError(BAD_REPLY, RETRY_HINT)
        chunks.append(chunk)
    return b"".join(chunks)


def _get_json(url):
    """Fetch a URL and return its JSON body, which must be an object."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            body = _read_limited(response)
    except CatalogueError:
        raise
    except (OSError, http.client.HTTPException) as exc:
        raise CatalogueError(NETWORK_ERROR, CONNECTION_HINT) from exc

    try:
        data = json.loads(body.decode("utf-8"))
    except ValueError as exc:  # Includes JSONDecodeError and UnicodeDecodeError.
        raise CatalogueError(BAD_REPLY, RETRY_HINT) from exc
    if not isinstance(data, dict):
        raise CatalogueError(BAD_REPLY, RETRY_HINT)
    return data


def fetch_page(page):
    """Return one page of the catalogue as a dict with 'count' and 'results'."""
    return _get_json(f"{API_URL}?page={page}")


def _results_of(page_data):
    results = page_data.get("results")
    if not isinstance(results, list):
        raise CatalogueError(BAD_REPLY, RETRY_HINT)
    return results


class Catalogue:
    """Random access to the most popular books, caching pages for the session."""

    def __init__(self, rng=None):
        self._rng = rng if rng is not None else random
        self._count = None  # Total books reported by Gutendex, loaded once.
        self._pages = {}  # page number -> results list

    def _load_first_page(self):
        if self._count is None:
            first = fetch_page(1)
            count = first.get("count", 0)
            if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
                raise CatalogueError(EMPTY_CATALOGUE)
            results = _results_of(first)
            if not results:
                raise CatalogueError(EMPTY_CATALOGUE)
            self._count = count
            self._pages[1] = results
        return self._count

    def _page(self, page_number):
        if page_number not in self._pages:
            self._pages[page_number] = _results_of(fetch_page(page_number))
        return self._pages[page_number]

    def random_book(self):
        """Pick a book uniformly at random from the most popular books in the catalogue."""
        count = self._load_first_page()
        pool = min(count, POPULAR_PAGES * PAGE_SIZE)
        for _ in range(MAX_ATTEMPTS):
            index = self._rng.randrange(pool)
            page_number, position = divmod(index, PAGE_SIZE)
            page_number += 1  # Gutendex pages start at 1.
            results = self._page(page_number)
            # The last page can be shorter than PAGE_SIZE; retry if the index falls outside it.
            if position < len(results) and isinstance(results[position], dict):
                return results[position]
        raise CatalogueError(NO_BOOK_FOUND, RETRY_HINT)
