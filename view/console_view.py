from services.account_service import AccountService
from services.custom_field_service import CustomFieldService
from utils.utils import create_database, get_db_session


def ask_for_key():
    print("Please enter the master password:")
    key = input()
    return key


def start_console_view():
    print("Program run in command line mode")
    key = ask_for_key()
    with get_db_session() as db_session:
        db = db_session
    Account, CustomField = create_database(key)
    custom_field_service = CustomFieldService(db, CustomField)
    account_service = AccountService(db, Account)
