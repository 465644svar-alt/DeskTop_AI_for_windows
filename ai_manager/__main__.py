"""
AI Manager - Entry Point
Run with: python -m ai_manager
"""

from .app import AIManagerApp


def main():
    """Main entry point"""
    app = AIManagerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
