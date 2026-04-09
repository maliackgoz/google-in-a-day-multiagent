#!/usr/bin/env python3
"""Entry point: start the HTTP UI/API (default port 3600)."""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from web.server import main

if __name__ == "__main__":
    main()
