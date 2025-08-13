"""
Main entry point for the Password Manager application.

This script allows the user to start the application in either GUI or console mode,
depending on the command-line argument provided.
"""

import argparse

from view.console_view import start_console_view

# from view.gui_view import start_gui_view
from view.gui_view_qt6 import start_gui_view


def main():
    """
    Parse command-line arguments and start the application in the selected mode.

    --mode console : Run the application in console (CLI) mode.
    --mode gui     : Run the application in graphical (GUI) mode.
    """
    parser = argparse.ArgumentParser(description="Password Manager Application")
    parser.add_argument(
        "--mode",
        choices=["console", "gui"],
        default="gui",
        help="Choose the mode to run the application: 'console' or 'gui'. Default is 'console'.",
    )

    args = parser.parse_args()

    if args.mode == "console":
        # Start the application in console mode
        start_console_view()
    elif args.mode == "gui":
        # Start the application in GUI mode
        start_gui_view()


if __name__ == "__main__":
    # Run the main function if this script is executed directly
    main()
