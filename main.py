#!/usr/bin/env python3
"""
AI Manager Desktop Application v11.0
Modern Multi-Model AI Desktop Application for Windows

Run: python main.py
Or:  python -m ai_manager
"""

import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_manager.app import AIManagerApp


def main():
    """Main entry point"""
    app = AIManagerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
