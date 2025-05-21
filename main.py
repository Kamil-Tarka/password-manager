import argparse

from view.console_view import start_console_view
from view.gui_view import start_gui_view


def main():
    parser = argparse.ArgumentParser(description="Password Manager Application")
    parser.add_argument(
        "--mode",
        choices=["console", "gui"],
        default="gui",
        help="Choose the mode to run the application: 'console' or 'gui'. Default is 'console'.",
    )

    args = parser.parse_args()

    if args.mode == "console":
        start_console_view()
    elif args.mode == "gui":
        start_gui_view()


if __name__ == "__main__":
    main()
