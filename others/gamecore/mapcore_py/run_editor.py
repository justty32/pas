"""World Sculptor launch script.

Usage:
    python run_editor.py
    python run_editor.py --width 80 --height 60

Requirements: pip install dearpygui
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from editor.app import App


def main() -> None:
    parser = argparse.ArgumentParser(description="World Sculptor — mapcore_py interactive map editor")
    parser.add_argument("--width",  type=int, default=60, help="Map width in hex tiles")
    parser.add_argument("--height", type=int, default=40, help="Map height in hex tiles")
    args = parser.parse_args()

    app = App(width=args.width, height=args.height)
    app.run()


if __name__ == "__main__":
    main()
