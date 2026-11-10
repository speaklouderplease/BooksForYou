# BooksForYou

Can't decide what to read next? BooksForYou picks a random free, public-domain book from the
[Gutendex](https://gutendex.com) catalogue of [Project Gutenberg](https://www.gutenberg.org) and
shows you its title, author and a link to read it online. The pick is random among the 320 most
popular (most downloaded) books, so you get a well-known classic each time.

## Requirements

- Python 3.10 or newer
- An internet connection

No third-party packages are needed; the app uses only the Python standard library.

## Usage

From the project folder, run:

```bash
python -m booksforyou
```

Each run shows one book. Press **Enter** for another, or type **q** to quit.

Example:

```
Title:  Pride and Prejudice
Author: Jane Austen (1775-1817)
Read:   https://www.gutenberg.org/ebooks/1342
```

Note that the catalogue only contains public-domain books, mostly older classics.
Gutendex does not provide publication dates, so the year shown is the author's lifespan.

## Running the tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## Project layout

```
booksforyou/
  api.py        # Gutendex access and random selection
  app.py        # interactive command-line loop and display formatting
  __main__.py   # entry point for `python -m booksforyou`
tests/
  test_booksforyou.py
```

## Known issues

- Gutendex can be slow or unreachable at times. If so, the app prints a message and exits.
  It does not retry.
- The pick is limited to the 320 most-downloaded books. Gutendex is very slow to serve deeper
  pages, so the wider catalogue is not sampled.

## Licence

MIT. See [LICENSE](LICENSE).
