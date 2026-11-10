"""Interactive command-line interface for BooksForYou."""

from .api import CatalogueError, random_book

BOOK_URL = "https://www.gutenberg.org/ebooks/{}"


def _format_author(author):
    name = author.get("name") or "Unknown author"
    # Gutendex stores names as "Last, First"; show them as "First Last".
    if ", " in name:
        last, first = name.split(", ", 1)
        name = f"{first} {last}"
    birth, death = author.get("birth_year"), author.get("death_year")
    if birth is not None and death is not None:
        name += f" ({birth}-{death})"
    elif birth is not None:
        name += f" (born {birth})"
    elif death is not None:
        name += f" (died {death})"
    return name


def format_book(book):
    """Return a human-readable multi-line description of a Gutendex book record."""
    title = book.get("title") or "Untitled"
    authors = book.get("authors") or []
    author_text = "; ".join(_format_author(a) for a in authors) or "Unknown author"
    lines = [
        f"Title:  {title}",
        f"Author: {author_text}",
        f"Read:   {BOOK_URL.format(book.get('id'))}",
    ]
    return "\n".join(lines)


def run(input_func=input, output=print, picker=random_book):
    """Run the interactive loop. Returns a process exit code."""
    output("Welcome to BooksForYou - a random pick from public-domain classics.")
    while True:
        try:
            book = picker()
        except CatalogueError as exc:
            output(f"Sorry, {exc} Check your internet connection and try again later.")
            return 1

        output("")
        output(format_book(book))

        try:
            answer = input_func("\nPress Enter for another book, or type q to quit: ")
        except (EOFError, KeyboardInterrupt):
            output("")
            output("Happy reading!")
            return 0

        if answer.strip().lower() in ("q", "quit", "exit"):
            output("Happy reading!")
            return 0
