#!/usr/bin/env python3
"""Thin wrapper — delegates to claude_cli._bus.

Usage:
    uv run bus read [N]
    uv run bus write '<json>'
    uv run bus metrics [N]
    uv run bus heartbeat <name>
    uv run bus sessions
"""

import sys
import os

# Add src to path so the module is importable when run directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from claude_cli._bus import main

main()
