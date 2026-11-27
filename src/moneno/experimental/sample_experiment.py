"""Example experiment: prints the arguments it receives."""

import sys


def main() -> None:
    print(sys.argv[1:])


if __name__ == "__main__":
    main()
