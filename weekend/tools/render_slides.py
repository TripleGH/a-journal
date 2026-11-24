#!/usr/bin/env python3
"""Old name, kept so earlier instructions still work.

The slide maker is tools/make_slides.py (the garden look, November 20, 2026). This file only passes the
call along, so `python3 tools/render_slides.py slides.json out` makes the new slides too.
"""
import sys

from make_slides import main

if __name__ == "__main__":
    main(sys.argv[1:])
