import sys
from datetime import datetime

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
    check_password_strength,
    coppy_to_clipboard,
    create_database,
    get_db_session,
)


def ask_for_key():
    print("Please enter the master password: ")
    key = input()
    return key


def print_main_menu():
    print("Select option:")
    print("1 - list all stored accounts")
    print("2 - select account")
    print("3 - add new account")
    print("4 - edit account")
    print("5 - delete account")
    print("6 - exit program")


def print_account_data(account):
    data = {
        "Id": account.id,
        "Title": account.title,
        "User name": account.user_name,
        "URL": account.url,
        "Notes": account.notes,
        "Expiration Date": account.expiration_date,
    }

    table_data = [[key] + value for key, value in data.items()]

    print("Account:")
    print(tabulate(table_data, headers=["Field name", "Value"], tablefmt="fancy_grid"))

    if account.custom_fields:
        custom_fields_data = [
            [field.id, field.name, field.value] for field in account.custom_fields
        ]
        print("\nCustom Fields:")
        print(
            tabulate(
                custom_fields_data,
                headers=["Id", "Name", "Value"],
                tablefmt="fancy_grid",
            )
        )
    else:
        print("\nCustom Fields: None")


def list_all_accounts(account_service: AccountService):
    entries = account_service.get_all()
    if not entries:
        print("No entries")
        return None
    table_data = [
        [
            entry.id,
            entry.title,
            entry.user_name,
            entry.url,
            entry.notes,
            entry.expiration_date,
        ]
        for entry in entries
    ]
    headers = ["Id", "Title", "Username", "URL", "Notes", "Expiration date"]
    print(tabulate(table_data, headers, tablefmt="grid"))
    return entries


def select_field_by_name(account):
    field_name = input("Please provide field name: ")
    if hasattr(account, field_name):
        return getattr(account, field_name)
    else:
        print(f"Field {field_name} does not exists.")
        return None


def select_account(account_service: AccountService):
    account_id = int(input("Provide account id: "))
    account = account_service.get_by_id(account_id)
    print("Selected account")
    print_account_data(account)
    print("1 - coppy data to clipboard")
    print("2 - go back")
    option = input("Select option: ")
    match option:
        case "1":
            value = select_field_by_name(account)
            if value:
                coppy_to_clipboard(value)
        case "2":
            return


def add_new_account(account_service: AccountService):
    title = str(input("Please provide account title: "))
    user_name = str(input("Please provide user name: "))
    password = str(input("Please provide password: "))

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
    print("Please provide new data, all data are optional")
    title = str(input("Please provide account title: "))
    user_name = str(input("Please provide user name: "))
    password = str(input("Please provide password: "))

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
    print("Provide custom field data")
    name = input("Please provide custom field name: ")
    value = input("Please provide custom vield value")
    new_custom_field_dto = CreateCustomFieldDTO(
        name=name, value=value, account_id=account.id
    )
    new_custom_field = custom_field_service.create(new_custom_field_dto)
    print_account_data(account)
    return new_custom_field


def update_custom_field(custom_field_service: CustomFieldService, account):
    cusotm_field_id = int(input("Provide custom field Id: "))
    custom_field = custom_field_service.get_by_id(cusotm_field_id)
    if custom_field.account_id != account.id:
        print("Wrong custom field Id")
        return
    print("Please provide new data, all fields are optional")
    new_name = input("Please provide new name: ")
    new_value = input("Please provide new value: ")
    custom_field_dto = UpdateCustomFieldDTO(name=new_name, value=new_value)
    custom_field = custom_field_service.update(custom_field.id, custom_field_dto)
    print_account_data(account)
    return custom_field


def delete_custom_field(custom_field_service: CustomFieldService, account):
    cusotm_field_id = int(input("Provide custom field Id: "))
    custom_field = custom_field_service.get_by_id(cusotm_field_id)
    if custom_field.account_id != account.id:
        print("Wrong custom field Id")
        return
    result = custom_field_service.delete(custom_field.id)
    print_account_data(account)
    return result


def update_account(
    account_service: AccountService, custom_field_service: CustomFieldService
):
    account_id = int(input("Provide account id to update: "))
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
            update_custom_field(custom_field_service, account)
        case "4":
            delete_custom_field(account, custom_field_service)
        case "5":
            return


def delete_account(account_service: AccountService):
    account_id = int(input("Please provide account id: "))
    result = False
    try:
        result = account_service.delete(account_id)
    except NotFoundAccountException as e:
        print(f"Error: {e}")
        return result
    return result


def start_console_view():
    print("Program run in command line mode")
    key = ask_for_key()
    with get_db_session() as db_session:
        db = db_session
    Account, CustomField = create_database(key)
    custom_field_service = CustomFieldService(db, CustomField, Account)
    account_service = AccountService(db, Account)
    accounts = list_all_accounts(account_service)
    while True:
        print_main_menu()
        option = input("Select option: ")
        match option:
            case "1":
                accounts = list_all_accounts(account_service)
            case "2":
                account = select_account(account_service)
            case "3":
                add_new_account(account_service)
            case "4":
                update_account(account_service, custom_field_service)
            case "5":
                delete_account(account_service)
            case "6":
                print("Exit program")
                sys.exit(0)
            case _:
                print("Invalid option. Please try again.")
