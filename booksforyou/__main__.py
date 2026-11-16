import argparse
import sys

from .app import run as run_session


def run(argv=None):
    parser = argparse.ArgumentParser(
        prog="booksforyou",
        description="Pick a random free, public-domain book.",
        allow_abbrev=False,
    )
    parser.parse_args(argv)
    return run_session()


if __name__ == "__main__":
    sys.exit(run())
