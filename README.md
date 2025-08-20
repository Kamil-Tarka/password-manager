# Password Manager

This is a simple password manager application that allows you to store and manage your account credentials securely. The application supports both a graphical user interface (GUI) and a command-line interface (CLI). All sensitive data is encrypted using AES encryption to ensure that your passwords and other information are kept safe.

## Features

- **Secure Encryption:** All your account data, including passwords, usernames, and custom fields, is encrypted using AES with a master password.
- **GUI and CLI Modes:** Choose between a user-friendly graphical interface or a fast and efficient command-line interface.
- **Password Generation:** Generate strong, random passwords with customizable length and character sets (digits, uppercase, special characters).
- **Password Strength Checker:** Get an estimate of the strength of your passwords.
- **Custom Fields:** Store additional information for each account using custom fields.
- **Cross-Platform:** The application is built with Python and PyQt6, making it compatible with Windows, macOS, and Linux.
- **Local Storage:** All data is stored locally in a SQLite database file (`passwords.db`).

## Installation from source

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/password-manager.git
    cd password-manager
    ```
2.  **Create a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
    ```
3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

You can run the application in either GUI mode or console mode.

### GUI Mode (Default)

To run the application in GUI mode, simply run the `main.py` script without any arguments:

```bash
python main.py
```

or

```bash
python main.py --mode gui
```

The first time you run the application, you will be prompted to create a master password. This password will be used to encrypt your data, so be sure to choose a strong one and remember it.

### Console Mode

To run the application in console mode, use the `--mode console` argument:

```bash
python main.py --mode console
```

The console mode provides a menu-driven interface for managing your accounts.

## Project Structure

```
password-manager/
├── .gitignore
├── database_settings.py      # SQLAlchemy database configuration
├── main.py                   # Main entry point for the application
├── requirements.txt          # Python dependencies
├── assets/                   # Icons and other assets
│   ├── icon.ico
│   └── icon.png
├── exceptions/               # Custom exception classes
│   ├── __init__.py
│   └── exceptions.py
├── models/                   # Pydantic models and SQLAlchemy entities
│   ├── __init__.py
│   ├── entities.py
│   └── models.py
├── services/                 # Business logic for the application
│   ├── __init__.py
│   ├── account_service.py
│   └── custom_field_service.py
├── utils/                    # Utility functions
│   ├── __init__.py
│   └── utils.py
└── view/                     # GUI and console views
    ├── __init__.py
    ├── console_view.py
    └── gui_view.py
```

## Dependencies

The main dependencies for this project are:

-   **SQLAlchemy:** For database interactions.
-   **SQLAlchemy-Utils:** For data encryption.
-   **Pydantic:** For data validation.
-   **Cryptography:** For cryptographic operations.
-   **PyQt6:** For the graphical user interface.
-   **Tabulate:** For displaying data in tables in the console view.
-   **Pyperclip:** For copying data to the clipboard.

For a full list of dependencies, see the `requirements.txt` file.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
