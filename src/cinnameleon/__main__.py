"""Allow Cinnameleon to run with python -m cinnameleon."""

from cinnameleon.cli import main

if __name__ == "__main__":
    raise SystemExit(main())