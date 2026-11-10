"""Interactive command-line interface for BooksForYou."""

import re

from .api import CatalogueError, Catalogue

BOOK_URL = "https://www.gutenberg.org/ebooks/{}"
WELCOME = "Welcome to BooksForYou - a random pick from public-domain classics."
PROMPT = "\nPress Enter for another book, or type q to quit: "
QUIT_WORDS = ("q", "quit", "exit")
CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f-\x9f]+")


def _clean(text):
    """Make remote text safe to print: replace control characters (such as escape codes)."""
    return CONTROL_CHARS.sub(" ", str(text)).strip()


def _year(value):
    """Return a year as text, or None if the value is not a whole number."""
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return None


def _format_author(author):
    name = _clean(author.get("name") or "Unknown author")
    # Gutendex stores names as "Last, First"; show them as "First Last".
    if ", " in name:
        last, first = name.split(", ", 1)
        name = f"{first} {last}"
    birth = _year(author.get("birth_year"))
    death = _year(author.get("death_year"))
    if birth and death:
        name += f" ({birth}-{death})"
    elif birth:
        name += f" (born {birth})"
    elif death:
        name += f" (died {death})"
    return name


def _format_authors(authors):
    if not isinstance(authors, list):
        return "Unknown author"
    names = [_format_author(a) for a in authors if isinstance(a, dict)]
    return "; ".join(names) or "Unknown author"


def _link(book_id):
    if isinstance(book_id, int) and not isinstance(book_id, bool):
        return BOOK_URL.format(book_id)
    return "unavailable"


def format_book(book):
    """Return a human-readable multi-line description of a Gutendex book record."""
    title = _clean(book.get("title") or "Untitled")
    lines = [
        f"Title:  {title}",
        f"Author: {_format_authors(book.get('authors'))}",
        f"Read:   {_link(book.get('id'))}",
    ]
    return "\n".join(lines)


def _error_text(error):
    if error.hint:
        return f"Sorry, {error.message} {error.hint}"
    return f"Sorry, {error.message}"


def run(input_func=input, output=print, picker=None):
    """Run the interactive loop. Returns a process exit code."""
    if picker is None:
        picker = Catalogue().random_book  # One catalogue per run, so pages are cached.

    output(WELCOME)
    try:
        while True:
            output("")
            output("Finding a book...")
            try:
                book = picker()
            except CatalogueError as exc:
                output(_error_text(exc))
                return 1

            output("")
            output(format_book(book))

            answer = input_func(PROMPT)
            if answer.strip().lower() in QUIT_WORDS:
                break
    except (EOFError, KeyboardInterrupt):
        output("")  # Ctrl+C or closed input: leave cleanly.

    output("Happy reading!")
    return 0
