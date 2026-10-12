"""Acquire, clean and validate datasets. Run from backend/:

uv run python -m scripts.download_datasets [--refresh | --offline] [--strict]
"""

import sys

from app.data_pipeline.cli import main

if __name__ == "__main__":
    sys.exit(main())
