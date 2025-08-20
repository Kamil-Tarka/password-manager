import getpass
import os
import sys
from datetime import datetime

from sqlalchemy_utils.types.encrypted.padding import InvalidPaddingError
from tabulate import tabulate

from exceptions.exceptions import NotFoundAccountException
from models.models import (
    CreateAccountDTO,
    CreateCustomFieldDTO,
    UpdateAccountDTO,
    UpdateCustomFieldDTO,
)
from services.account_service import AccountService
from services.custom_field_service import CustomFieldService
from utils.utils import (
    check_if_db_exists,
    check_if_db_is_empty,
    check_password_strength,
    coppy_to_clipboard,
    create_database,
    create_salt,
    derive_key,
    generate_password,
    get_db_session,
    is_key_valid,
    load_salt,
)

# ANSI color codes for console coloring
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"


def _get_expiration_color(expiration_date):
    """Return color code (RED/YELLOW) based on expiration_date or None."""
    if not expiration_date:
        return None
    try:
        if isinstance(expiration_date, datetime):
            exp_date = expiration_date.date()
        else:
            # Try common formats
            try:
                exp_date = datetime.strptime(str(expiration_date), "%d-%m-%Y").date()
            except Exception:
                try:
                    exp_date = datetime.strptime(
                        str(expiration_date), "%Y-%m-%d"
                    ).date()
                except Exception:
                    return None
    except Exception:
        return None
    today = datetime.now().date()
    delta_days = (exp_date - today).days
    if delta_days < 0:
        return RED
    if delta_days <= 10:
        return YELLOW
    return None


def _color_text(text, color):
    if not color:
        return text
    return f"{color}{text}{RESET}"


def ask_for_master_password(salt):
    """
    Prompt the user to enter the master password (encryption key).
    Returns:
        str: The entered master password.
    """
    print("Please enter the master password: ")
    master_password = getpass.getpass("Master password: ")
    encryption_key = str(derive_key(master_password, salt))
    return encryption_key


def print_main_menu():
    """
    Print the main menu options for the console application.
    """
    print("Select option:")
    print("1 - list all stored accounts")
    print("2 - select account")
    print("3 - add new account")
    print("4 - edit account")
    print("5 - delete account")
    print("6 - clear console")
    print("7 - exit program")


def clear_console():
    """
    Clear the console screen.
    """
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")


def print_account_data(account):
    """
    Print detailed information about an account, including custom fields.

    Args:
        account: The account object to display.
    """
    color = _get_expiration_color(getattr(account, "expiration_date", None))

    data = [
        ["Id", _color_text(str(account.id), color)],
        ["Title", _color_text(str(account.title or ""), color)],
        ["User name", _color_text(str(account.user_name or ""), color)],
        ["Password", _color_text("*" * len(account.password or ""), color)],
        ["URL", _color_text(str(account.url or ""), color)],
        ["Notes", _color_text(str(account.notes or ""), color)],
        ["Expiration Date", _color_text(str(account.expiration_date or ""), color)],
    ]

    print("Account:")
    print(tabulate(data, tablefmt="fancy_grid"))

    if hasattr(account, "custom_fields") and account.custom_fields:
        custom_fields_data = [
            [
                _color_text(str(field.id), color),
                _color_text(str(field.name), color),
                _color_text(str(field.value), color),
            ]
            for field in account.custom_fields
        ]
        print("\nCustom Fields:")
        print(
            tabulate(
                custom_fields_data,
                headers=[
                    _color_text("Id", color),
                    _color_text("Name", color),
                    _color_text("Value", color),
                ],
                tablefmt="fancy_grid",
            )
        )
    else:
        print("\nCustom Fields: None")


def list_all_accounts(account_service: AccountService):
    """
    List all accounts in a tabular format.

    Args:
        account_service: Service for account operations.

    Returns:
        list: List of account entries.
    """
    entries = account_service.get_all()
    if not entries:
        print("No accounts found.")
        return None

    table_data = []
    for entry in entries:
        color = _get_expiration_color(getattr(entry, "expiration_date", None))
        row = [
            _color_text(str(entry.id), color),
            _color_text(str(entry.title or ""), color),
            _color_text(str(entry.user_name or ""), color),
            _color_text("*" * len(entry.password or ""), color),
            _color_text(str(entry.url or ""), color),
            _color_text(str(entry.notes or ""), color),
            _color_text(str(entry.expiration_date or ""), color),
        ]
        table_data.append(row)

    headers = [
        "Id",
        "Title",
        "User name",
        "Password",
        "URL",
        "Notes",
        "Expiration date",
    ]
    print(tabulate(table_data, headers, tablefmt="fancy_grid"))
    return entries


def select_field_by_name(account):
    """
    Allow the user to select a field or custom field from an account to copy to clipboard.

    Args:
        account: The account object.

    Returns:
        str or None: The value of the selected field, or None if not found.
    """
    print(
        "To coppy account data to clipboard, please provide field name, to copy custom field, please provide 'custom field' first"
    )
    field_name = input("Please provide field name: ").lower()
    if field_name == "" or field_name is None:
        print("Field name cannot be empty, please provide field name.")
        return None
    if " " in field_name:
        field_name = field_name.replace(" ", "_")
    if hasattr(account, field_name):
        return getattr(account, field_name)
    elif field_name.lower() == "custom_field" and account.custom_fields:
        custom_field_id = int(input("Please provide custom field id to coppy: "))
        if custom_field_id is None or custom_field_id < 0:
            print("Invalid custom field id. Please enter a positive number.")
            return None
        field_name = input("Please provide custom field name: ").lower()
        if field_name == "" or field_name is None:
            print("Field name cannot be empty, please provide field name.")
            return None
        custom_fields = account.custom_fields
        custom_field = next(
            (obj for obj in custom_fields if obj.id == custom_field_id), None
        )
        if not custom_field:
            print(f"Custom field with id {custom_field_id} does not exist.")
            return None
        if hasattr(custom_field, field_name):
            return getattr(custom_field, field_name)
        print(f"Custom field {field_name} does not exist.")
    else:
        print(f"Field {field_name} does not exist.")
    return None


def select_account(account_service: AccountService):
    """
    Allow the user to select an account by ID and perform actions (copy, show password).

    Args:
        account_service: Service for account operations.
    """
    try:
        account_id = int(input("Provide account id: "))
    except ValueError:
        print("Invalid account id. Please enter a number.")
        return None
    try:
        account = account_service.get_by_id(account_id)
    except NotFoundAccountException as e:
        print(f"Error: {e}")
        return None
    print("Selected account")
    print_account_data(account)
    print("1 - coppy data to clipboard")
    print("2 - show password")
    print("3 - go back")
    option = input("Select option: ")
    match option:
        case "1":
            value = select_field_by_name(account)
            if value:
                coppy_to_clipboard(value)
        case "2":
            print("Password: ", account.password)
        case "3":
            return


def add_new_account(account_service: AccountService):
    """
    Prompt the user to add a new account, including password generation and strength check.

    Args:
        account_service: Service for account operations.

    Returns:
        The created account object.
    """
    title = str(input("Please provide account title: "))
    if title == "" or title is None:
        print("Title cannot be empty, please provide title.")
        return None
    user_name = str(input("Please provide user name: "))
    if user_name == "" or user_name is None:
        print("User name cannot be empty, please provide user name.")
        return None
    ask_generate_password = input("Do you want to generate password? (y/n): ")
    if ask_generate_password.lower() == "y":
        length = int(input("Please provide password length: "))
        use_digits = input("Use digits? (y/n): ").lower() == "y"
        use_uppercase = input("Use uppercase letters? (y/n): ").lower() == "y"
        use_special = input("Use special characters? (y/n): ").lower() == "y"
        password = generate_password(length, use_digits, use_uppercase, use_special)
    else:
        password = getpass.getpass("Please provide password: ")
        if password == "" or password is None:
            print("Password cannot be empty, please provide password.")
            return None

    password_strengh = check_password_strength(password)
    print(f"This password is {password_strengh.lower()}")

    url = str(input("(Optional value) Please provide URL: "))
    notes = str(input("(Optional value) Please provide notes: "))
    expiration_date_str = input(
        "(Optional value, input format: DD-MM-YYYY) Please provide expiration date: "
    )
    expiration_date = None
    if expiration_date_str:
        try:
            expiration_date = datetime.strptime(expiration_date_str, "%d-%m-%Y")
        except ValueError:
            print("Invalid date format. Please use DD-MM-YYYY.")
            print(
                "Expiration date won't be set, you can add it later by editing account."
            )
            expiration_date = None

    new_account = CreateAccountDTO(
        title=title,
        user_name=user_name,
        password=password,
        url=url,
        notes=notes,
        expiration_date=expiration_date,
    )
    created_account = account_service.create(new_account)
    return created_account


def edit_account_data(account, account_service: AccountService):
    """
    Edit the data of an existing account.

    Args:
        account: The account object to edit.
        account_service: Service for account operations.

    Returns:
        The updated account object.
    """
    print(
        "Please provide new data, all data are optional\nif you don't want to change field, just press enter"
    )
    title = str(input("Please provide account title: "))
    user_name = str(input("Please provide user name: "))
    ask_generate_password = input("Do you want to generate password? (y/n): ")
    if ask_generate_password.lower() == "y":
        length = int(input("Please provide password length: "))
        use_digits = input("Use digits? (y/n): ").lower() == "y"
        use_uppercase = input("Use uppercase letters? (y/n): ").lower() == "y"
        use_special = input("Use special characters? (y/n): ").lower() == "y"
        password = generate_password(length, use_digits, use_uppercase, use_special)
    else:
        password = getpass.getpass("Please provide password: ")
    if password:
        password_strengh = check_password_strength(password)
        print(f"This password is {password_strengh.lower()}")

    url = str(input("(Optional value) Please provide URL: "))
    notes = str(input("(Optional value) Please provide notes: "))
    expiration_date_str = input(
        "(Optional value, input format: DD-MM-YYYY) Please provide expiration date: "
    )
    expiration_date = None
    if expiration_date_str:
        try:
            expiration_date = datetime.strptime(expiration_date_str, "%d-%m-%Y")
        except ValueError:
            print("Invalid date format. Please use DD-MM-YYYY.")
            print(
                "Expiration date won't be set, you can add it later by editing account."
            )
            expiration_date = None
    update_account = UpdateAccountDTO(
        title=title,
        user_name=user_name,
        password=password,
        url=url,
        notes=notes,
        expiration_date=expiration_date,
    )
    updated_account = account_service.update(account.id, update_account)
    print_account_data(updated_account)
    return updated_account


def add_new_custom_field(account, custom_field_service: CustomFieldService):
    """
    Add a new custom field to an account.

    Args:
        account: The account object.
        custom_field_service: Service for custom field operations.

    Returns:
        The created custom field object.
    """
    print("Provide custom field data")
    name = input("Please provide custom field name: ")
    if name == "" or name is None:
        print("Custom field name cannot be empty, please provide name.")
        return None
    value = input("Please provide custom field value: ")
    if value == "" or value is None:
        print("Custom field value cannot be empty, please provide value.")
        return None
    new_custom_field_dto = CreateCustomFieldDTO(
        name=name, value=value, account_id=account.id
    )
    new_custom_field = custom_field_service.create(new_custom_field_dto)
    print_account_data(account)
    return new_custom_field


def update_custom_field(account, custom_field_service: CustomFieldService):
    """
    Update an existing custom field for an account.

    Args:
        account: The account object.
        custom_field_service: Service for custom field operations.

    Returns:
        The updated custom field object.
    """
    try:
        cusotm_field_id = int(input("Provide custom field Id: "))
    except ValueError:
        print("Invalid custom field id. Please enter a number.")
        return None
    try:
        custom_field = custom_field_service.get_by_id(cusotm_field_id)
    except NotFoundAccountException as e:
        print(f"Error: {e}")
        return None
    if custom_field.account_id != account.id:
        print("Wrong custom field Id")
        return
    print(
        "Please provide new data, all fields are optional\nif you don't want to change field, just press enter"
    )
    new_name = input("Please provide new name: ")
    new_value = input("Please provide new value: ")
    custom_field_dto = UpdateCustomFieldDTO(name=new_name, value=new_value)
    custom_field = custom_field_service.update(custom_field.id, custom_field_dto)
    print_account_data(account)
    return custom_field


def delete_custom_field(account, custom_field_service: CustomFieldService):
    """
    Delete a custom field from an account.

    Args:
        account: The account object.
        custom_field_service: Service for custom field operations.

    Returns:
        Result of the delete operation.
    """
    try:
        cusotm_field_id = int(input("Provide custom field Id: "))
    except ValueError:
        print("Invalid custom field id. Please enter a number.")
        return None
    try:
        custom_field = custom_field_service.get_by_id(cusotm_field_id)
    except NotFoundAccountException as e:
        print(f"Error: {e}")
        return None
    if custom_field.account_id != account.id:
        print("Wrong custom field Id")
        return
    result = custom_field_service.delete(cusotm_field_id)
    print_account_data(account)
    return result


def update_account(
    account_service: AccountService, custom_field_service: CustomFieldService
):
    """
    Update an account or its custom fields by presenting a menu of options.

    Args:
        account_service: Service for account operations.
        custom_field_service: Service for custom field operations.
    """
    try:
        account_id = int(input("Provide account id to update: "))
    except ValueError:
        print("Invalid account id. Please enter a number.")
        return None
    try:
        account = account_service.get_by_id(account_id)
    except NotFoundAccountException as e:
        print(f"Error: {e}")
        return None
    print_account_data(account)
    print("1 - edit account data")
    print("2 - add new custom field")
    print("3 - edit custom field")
    print("4 - delete custom field")
    print("5 - go back")
    option = input("Select option: ")
    match option:
        case "1":
            edit_account_data(account, account_service)
        case "2":
            add_new_custom_field(account, custom_field_service)
        case "3":
            update_custom_field(account, custom_field_service)
        case "4":
            delete_custom_field(account, custom_field_service)
        case "5":
            return


def delete_account(account_service: AccountService):
    """
    Delete an account by ID after user confirmation.

    Args:
        account_service: Service for account operations.

    Returns:
        bool: True if deleted, False otherwise.
    """
    try:
        account_id = int(input("Please provide account id: "))
    except ValueError:
        print("Invalid account id. Please enter a number.")
        return None
    result = False
    try:
        account = account_service.get_by_id(account_id)
        if account:
            ask_for_delete = input("Do you want to delete this account? (y/n): ")
            if ask_for_delete.lower() == "y":
                result = account_service.delete(account_id)
                print("Account deleted")
            else:
                print("Account not deleted")
    except NotFoundAccountException as e:
        print(f"Error: {e}")
        return result
    return result


def start_console_view():
    """
    Entry point for the console (command-line) view of the Password Manager.

    Handles:
    - Master password prompt
    - Database and service setup
    - Main menu loop for account management
    - Error handling for invalid keys and missing accounts
    """
    clear_console()
    print(
        "Program run in command line mode\nPasswords inputs won't show any text that you provide in console."
    )
    salt = load_salt()
    if salt is None:
        salt = create_salt()
    while True:
        encryption_key = ask_for_master_password(salt)
        if check_if_db_exists():
            if is_key_valid(encryption_key):
                break
            else:
                print(
                    "Invalid master password. Please provide a valid master password."
                )
        else:
            break
    try:
        with get_db_session() as db_session:
            db = db_session
        Account, CustomField = create_database(encryption_key)
        custom_field_service = CustomFieldService(db, CustomField, Account)
        account_service = AccountService(db, Account)
    except InvalidPaddingError:
        sys.exit(0)
    if check_if_db_is_empty(account_service):
        print("Dataabase is empty, please add new account")
        add_new_account(account_service)
    list_all_accounts(account_service)
    while True:
        print_main_menu()
        option = input("Select option: ")
        match option:
            case "1":
                list_all_accounts(account_service)
            case "2":
                select_account(account_service)
            case "3":
                add_new_account(account_service)
            case "4":
                update_account(account_service, custom_field_service)
            case "5":
                delete_account(account_service)
            case "6":
                clear_console()
            case "7":
                print("Exit program")
                sys.exit(0)
            case _:
                print("Invalid option. Please try again.")
