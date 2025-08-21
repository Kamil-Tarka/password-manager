import sys
import threading
import time
from datetime import datetime

import pyperclip
from PyQt6 import QtCore, QtGui, QtWidgets

from models.models import CreateAccountDTO, CreateCustomFieldDTO, UpdateAccountDTO
from services.account_service import AccountService
from services.custom_field_service import CustomFieldService
from utils.utils import (
    check_if_db_exists,
    check_if_db_is_empty,
    check_password_strength,
    create_database,
    create_salt,
    derive_key,
    generate_password,
    get_db_session,
    is_key_valid,
    load_salt,
)


class MasterPasswordDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enter master password")
        self.setFixedSize(400, 200)
        layout = QtWidgets.QVBoxLayout(self)
        label = QtWidgets.QLabel("Please enter the master password:")
        label.setFont(QtGui.QFont("Arial", 12))
        layout.addWidget(label)
        self.key_entry = QtWidgets.QLineEdit()
        self.key_entry.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.key_entry.setFont(QtGui.QFont("Arial", 12))
        layout.addWidget(self.key_entry)
        self.show_btn = QtWidgets.QPushButton("Show password")
        self.show_btn.clicked.connect(self.toggle_password)
        layout.addWidget(self.show_btn)
        self.submit_btn = QtWidgets.QPushButton("Submit")
        self.submit_btn.clicked.connect(self.accept)
        layout.addWidget(self.submit_btn)
        self.key_entry.returnPressed.connect(self.accept)
        self.key_entry.setFocus()
        self.showing = False

    def toggle_password(self):
        if self.showing:
            self.key_entry.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
            self.show_btn.setText("Show password")
        else:
            self.key_entry.setEchoMode(QtWidgets.QLineEdit.EchoMode.Normal)
            self.show_btn.setText("Hide password")
        self.showing = not self.showing

    def get_key(self):
        return self.key_entry.text().strip()

    def accept(self):
        if not self.key_entry.text().strip():
            QtWidgets.QMessageBox.warning(
                self, "Warning", "Master password cannot be empty."
            )
            return
        super().accept()


class AccountTableModel(QtCore.QAbstractTableModel):
    def __init__(self, accounts, headers):
        super().__init__()
        self.accounts = accounts
        self.headers = headers
        self.sort_col = 0
        self.sort_order = QtCore.Qt.SortOrder.AscendingOrder

    def rowCount(self, parent=None):
        return len(self.accounts)

    def columnCount(self, parent=None):
        return len(self.headers)

    def data(self, index, role=QtCore.Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        acc = self.accounts[index.row()]
        col = index.column()
        # Display values
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return acc.id
            elif col == 1:
                return acc.title
            elif col == 2:
                return acc.user_name
            elif col == 3:
                return acc.url
            elif col == 4:
                val = acc.expiration_date
                if isinstance(val, datetime):
                    return val.strftime("%d-%m-%Y")
                elif val is not None:
                    return str(val)
                else:
                    return ""
            elif col == 5:
                return acc.notes

        # Foreground coloring based on expiration date
        if role == QtCore.Qt.ItemDataRole.ForegroundRole:
            val = getattr(acc, "expiration_date", None)
            if val is None or val == "":
                return None
            try:
                if isinstance(val, datetime):
                    exp_date = val.date()
                else:
                    exp_date = datetime.strptime(str(val), "%d-%m-%Y").date()
            except Exception:
                return None
            today = datetime.now().date()
            delta_days = (exp_date - today).days
            if delta_days < 0:
                return QtGui.QBrush(QtGui.QColor("#990000"))  # dark red for expired
            if delta_days <= 10:
                return QtGui.QBrush(
                    QtGui.QColor("#CC6600")
                )  # dark orange for soon-to-expire
        return None

    def headerData(self, section, orientation, role=QtCore.Qt.ItemDataRole.DisplayRole):
        if (
            orientation == QtCore.Qt.Orientation.Horizontal
            and role == QtCore.Qt.ItemDataRole.DisplayRole
        ):
            return self.headers[section]
        return None

    def sort(self, column, order):  # type: ignore
        # Sort accounts by selected column
        col_map = {
            0: "id",
            1: "title",
            2: "user_name",
            3: "url",
            4: "expiration_date",
            5: "notes",
        }
        attr = col_map.get(column, "id")
        if attr == "expiration_date":

            def sort_key(acc):
                val = getattr(acc, attr, None)
                if val is None or val == "":
                    # None/empty dates sort as far future for ascending, far past for descending
                    return (
                        datetime.max
                        if order == QtCore.Qt.SortOrder.AscendingOrder
                        else datetime.min
                    )
                if isinstance(val, datetime):
                    return val
                try:
                    # Try to parse string date
                    return datetime.strptime(str(val), "%d-%m-%Y")
                except Exception:
                    return (
                        datetime.max
                        if order == QtCore.Qt.SortOrder.AscendingOrder
                        else datetime.min
                    )

            self.accounts.sort(
                key=sort_key,
                reverse=(order == QtCore.Qt.SortOrder.DescendingOrder),
            )
        else:
            self.accounts.sort(
                key=lambda acc: getattr(acc, attr, ""),
                reverse=(order == QtCore.Qt.SortOrder.DescendingOrder),
            )
        self.sort_col = column
        self.sort_order = order
        self.layoutChanged.emit()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, account_service, custom_field_service):
        super().__init__()
        self.account_service = account_service
        self.custom_field_service = custom_field_service
        self.setWindowTitle("Password Manager")
        self.setGeometry(100, 100, 1024, 768)
        self.central = QtWidgets.QWidget()
        self.setCentralWidget(self.central)
        self.main_layout = QtWidgets.QVBoxLayout(self.central)

        # Filtering
        filter_layout = QtWidgets.QHBoxLayout()
        self.filter_title = QtWidgets.QLineEdit()
        self.filter_title.setPlaceholderText("Title")
        self.filter_user = QtWidgets.QLineEdit()
        self.filter_user.setPlaceholderText("User name")
        self.filter_url = QtWidgets.QLineEdit()
        self.filter_url.setPlaceholderText("URL")
        filter_layout.addWidget(QtWidgets.QLabel("Title:"))
        filter_layout.addWidget(self.filter_title)
        filter_layout.addWidget(QtWidgets.QLabel("User name:"))
        filter_layout.addWidget(self.filter_user)
        filter_layout.addWidget(QtWidgets.QLabel("URL:"))
        filter_layout.addWidget(self.filter_url)
        self.main_layout.addLayout(filter_layout)

        self.filter_title.textChanged.connect(self.refresh_table)
        self.filter_user.textChanged.connect(self.refresh_table)
        self.filter_url.textChanged.connect(self.refresh_table)

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton("Add Account")
        self.edit_btn = QtWidgets.QPushButton("Edit")
        self.del_btn = QtWidgets.QPushButton("Delete")
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.del_btn)
        self.main_layout.addLayout(btn_layout)
        self.add_btn.clicked.connect(self.add_account)
        self.edit_btn.clicked.connect(self.edit_account)
        self.del_btn.clicked.connect(self.delete_account)

        # Table
        self.headers = ["Id", "Title", "User name", "URL", "Expiration date", "Notes"]
        self.table = QtWidgets.QTableView()
        self.main_layout.addWidget(self.table)
        self.table.setSelectionBehavior(
            QtWidgets.QTableView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(QtWidgets.QTableView.SelectionMode.SingleSelection)
        self.table.doubleClicked.connect(self.edit_account)
        self.table.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.setSortingEnabled(True)
        header = self.table.horizontalHeader()
        if header is not None:
            header.sectionClicked.connect(self.on_section_clicked)

        self.last_sorted_col = None
        self.last_sort_order = QtCore.Qt.SortOrder.AscendingOrder

        self.refresh_table()

    def get_filters(self):
        return (
            self.filter_title.text(),
            self.filter_user.text(),
            self.filter_url.text(),
        )

    def refresh_table(self):
        title, user, url = self.get_filters()

        accounts = self.account_service.get_all()
        if title:
            accounts = [a for a in accounts if title.lower() in (a.title or "").lower()]
        if user:
            accounts = [
                a for a in accounts if user.lower() in (a.user_name or "").lower()
            ]
        if url:
            accounts = [a for a in accounts if url.lower() in (a.url or "").lower()]
        self.model = AccountTableModel(accounts, self.headers)
        self.table.setModel(self.model)
        self.table.resizeColumnsToContents()

        if self.last_sorted_col is not None:
            self.table.sortByColumn(self.last_sorted_col, self.last_sort_order)
        else:
            self.table.sortByColumn(0, QtCore.Qt.SortOrder.AscendingOrder)

    def get_selected_account(self):
        selection_model = self.table.selectionModel()
        if selection_model is None:
            return None
        idxs = selection_model.selectedRows()
        if not idxs:
            return None
        row = idxs[0].row()
        acc_id = self.model.accounts[row].id
        return self.account_service.get_by_id(acc_id)

    def add_account(self):
        dlg = AccountDialog(self, self.account_service, self.custom_field_service)
        if dlg.exec():
            self.refresh_table()

    def edit_account(self):
        acc = self.get_selected_account()
        if not acc:
            QtWidgets.QMessageBox.warning(self, "Warning", "No account selected.")
            return
        dlg = AccountDialog(self, self.account_service, self.custom_field_service, acc)
        if dlg.exec():
            self.refresh_table()

    def delete_account(self):
        acc = self.get_selected_account()
        if not acc:
            QtWidgets.QMessageBox.warning(self, "Warning", "No account selected.")
            return
        if (
            QtWidgets.QMessageBox.question(
                self, "Confirm", "Are you sure you want to delete this account?"
            )
            == QtWidgets.QMessageBox.StandardButton.Yes
        ):
            self.account_service.delete(acc.id)
            self.refresh_table()

    def show_context_menu(self, pos):
        acc = self.get_selected_account()
        menu = QtWidgets.QMenu(self)
        menu.addAction(
            "Copy user name",
            lambda: self.copy_to_clipboard(acc.user_name if acc else ""),
        )
        menu.addAction(
            "Copy password", lambda: self.copy_to_clipboard(acc.password if acc else "")
        )
        menu.addAction("Edit account", self.edit_account)
        menu.addAction("Delete account", self.delete_account)
        # Custom fields submenu
        other_data_menu = QtWidgets.QMenu("Coppy custom field", self)
        if acc and acc.custom_fields:
            for cf in acc.custom_fields:
                cf_name = getattr(cf, "name", None) or (
                    cf.get("name") if isinstance(cf, dict) else ""
                )
                cf_value = getattr(cf, "value", None) or (
                    cf.get("value") if isinstance(cf, dict) else ""
                )
                if cf_name:
                    other_data_menu.addAction(
                        f'Copy "{cf_name}" value',
                        lambda v=cf_value: self.copy_to_clipboard(v),
                    )
        else:
            no_fields_action = other_data_menu.addAction("No custom fields")
            if no_fields_action is not None:
                no_fields_action.setEnabled(False)
        menu.addMenu(other_data_menu)
        viewport = self.table.viewport()
        if viewport is not None:
            menu.exec(viewport.mapToGlobal(pos))
        else:
            menu.exec(self.mapToGlobal(pos))

    def copy_to_clipboard(self, value):
        def clear_clipboard():
            time.sleep(10)
            pyperclip.copy("")

        clipboard = QtWidgets.QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(str(value))
            clear_thread = threading.Thread(target=clear_clipboard)
            clear_thread.daemon = True
            clear_thread.start()

    def on_section_clicked(self, idx):
        if self.last_sorted_col == idx:
            self.last_sort_order = (
                QtCore.Qt.SortOrder.DescendingOrder
                if self.last_sort_order == QtCore.Qt.SortOrder.AscendingOrder
                else QtCore.Qt.SortOrder.AscendingOrder
            )
        else:
            self.last_sorted_col = idx
            self.last_sort_order = QtCore.Qt.SortOrder.AscendingOrder
        self.model.sort(idx, self.last_sort_order)
        self.table.sortByColumn(idx, self.last_sort_order)


class AccountDialog(QtWidgets.QDialog):
    def __init__(self, parent, account_service, custom_field_service, account=None):
        super().__init__(parent)
        self.account_service = account_service
        self.custom_field_service = custom_field_service
        self.account = account
        self.setWindowTitle("Edit Account" if account else "Add New Account")
        self.setMinimumWidth(480)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(
            QtWidgets.QLabel(
                'Fields marked with "*" are required.',
                font=QtGui.QFont("Arial", 10, italic=True),
            )  # type: ignore
        )

        # Fields
        self.fields = {}
        form = QtWidgets.QFormLayout()
        self.fields["Title"] = QtWidgets.QLineEdit()
        self.fields["User name"] = QtWidgets.QLineEdit()
        self.fields["Password"] = QtWidgets.QLineEdit()
        self.fields["Password"].setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.fields["URL"] = QtWidgets.QLineEdit()
        self.fields["Notes"] = QtWidgets.QPlainTextEdit()
        self.fields["Expiration date"] = QtWidgets.QLineEdit()
        form.addRow("Title*:", self.fields["Title"])
        form.addRow("User name*:", self.fields["User name"])
        pw_layout = QtWidgets.QHBoxLayout()
        pw_layout.addWidget(self.fields["Password"])
        self.show_btn = QtWidgets.QPushButton("Show password")
        self.show_btn.clicked.connect(self.toggle_password)
        pw_layout.addWidget(self.show_btn)
        form.addRow("Password*:", pw_layout)
        form.addRow("URL:", self.fields["URL"])
        form.addRow("Notes:", self.fields["Notes"])
        form.addRow("Expiration date (DD-MM-YYYY):", self.fields["Expiration date"])
        layout.addLayout(form)

        # Password strength
        self.pw_strength = QtWidgets.QLabel("Password strength: ")
        layout.addWidget(self.pw_strength)
        self.fields["Password"].textChanged.connect(self.update_pw_strength)

        # Password generator
        gen_btn = QtWidgets.QPushButton("Generate password")
        gen_btn.clicked.connect(self.generate_password)
        layout.addWidget(gen_btn)

        # Custom fields
        layout.addWidget(
            QtWidgets.QLabel(
                "Custom fields", font=QtGui.QFont("Arial", 10, QtGui.QFont.Weight.Bold)
            )  # type: ignore
        )
        self.custom_fields = []
        self.custom_fields_layout = QtWidgets.QVBoxLayout()
        layout.addLayout(self.custom_fields_layout)
        add_cf_btn = QtWidgets.QPushButton("Add custom field")
        add_cf_btn.clicked.connect(self.add_custom_field_row)
        layout.addWidget(add_cf_btn)
        self.custom_field_widgets = []

        # Buttons
        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        # Fill data if editing
        if account:
            self.fields["Title"].setText(account.title or "")
            self.fields["User name"].setText(account.user_name or "")
            self.fields["Password"].setText(account.password or "")
            self.fields["URL"].setText(account.url or "")
            self.fields["Notes"].setPlainText(account.notes or "")
            if account.expiration_date:
                if isinstance(account.expiration_date, datetime):
                    self.fields["Expiration date"].setText(
                        account.expiration_date.strftime("%d-%m-%Y")
                    )
                else:
                    self.fields["Expiration date"].setText(str(account.expiration_date))
            for cf in getattr(account, "custom_fields", []):
                self.add_custom_field_row(cf)
        else:
            self.add_custom_field_row()

        self.update_pw_strength()

    def toggle_password(self):
        if self.fields["Password"].echoMode() == QtWidgets.QLineEdit.EchoMode.Password:
            self.fields["Password"].setEchoMode(QtWidgets.QLineEdit.EchoMode.Normal)
            self.show_btn.setText("Hide password")
        else:
            self.fields["Password"].setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
            self.show_btn.setText("Show password")

    def update_pw_strength(self):
        pw = self.fields["Password"].text()
        strength = check_password_strength(pw)
        self.pw_strength.setText(f"Password strength: {strength}")

    def generate_password(self):
        dlg = PasswordGeneratorDialog(self)
        if dlg.exec():
            self.fields["Password"].setText(dlg.get_password())

    def add_custom_field_row(self, cf=None):
        row = QtWidgets.QHBoxLayout()
        name = QtWidgets.QLineEdit()
        value = QtWidgets.QLineEdit()
        cf_id = None
        if cf:
            name.setText(getattr(cf, "name", "") or cf.get("name", ""))
            value.setText(getattr(cf, "value", "") or cf.get("value", ""))
            cf_id = getattr(cf, "id", None) if hasattr(cf, "id") else cf.get("id", None)
        remove_btn = QtWidgets.QPushButton("Remove")

        def remove():
            if cf_id:
                self.custom_field_service.delete(cf_id)
            for i in reversed(range(row.count())):
                item = row.itemAt(i)
                if item is not None:
                    w = item.widget()
                    if w:
                        w.setParent(None)
            self.custom_fields_layout.removeItem(row)
            try:
                self.custom_fields.remove((name, value))
            except ValueError:
                pass
            try:
                self.custom_field_widgets.remove((name, value, cf_id))
            except ValueError:
                pass

        remove_btn.clicked.connect(remove)
        row.addWidget(name)
        row.addWidget(value)
        row.addWidget(remove_btn)
        self.custom_fields_layout.addLayout(row)
        self.custom_fields.append((name, value))
        self.custom_field_widgets.append((name, value, cf_id))

    def accept(self):
        title = self.fields["Title"].text().strip()
        user_name = self.fields["User name"].text().strip()
        password = self.fields["Password"].text()
        url = self.fields["URL"].text()
        notes = self.fields["Notes"].toPlainText()
        expiration_date_str = self.fields["Expiration date"].text().strip()
        expiration_date = None
        if expiration_date_str:
            try:
                expiration_date = datetime.strptime(expiration_date_str, "%d-%m-%Y")
            except ValueError:
                QtWidgets.QMessageBox.critical(
                    self, "Error", "Invalid date format. Use DD-MM-YYYY."
                )
                return
        if not title or not user_name or not password:
            QtWidgets.QMessageBox.critical(
                self, "Error", "Title, User name and Password are required."
            )
            return
        if self.account:
            update_account_dto = UpdateAccountDTO(
                title=title,
                user_name=user_name,
                password=password,
                url=url,
                notes=notes,
                expiration_date=expiration_date,
            )
            self.account_service.update(self.account.id, update_account_dto)
            current_custom_fields = []
            if hasattr(self.account, "custom_fields"):
                current_custom_fields = self.account.custom_fields
            existing_ids = set()
            for cf in current_custom_fields:
                cf_id = (
                    getattr(cf, "id", None) if hasattr(cf, "id") else cf.get("id", None)
                )
                if cf_id:
                    existing_ids.add(cf_id)
            form_ids = set()
            for name, value, cf_id in self.custom_field_widgets:
                n = name.text().strip()
                v = value.text().strip()
                if n:
                    if cf_id:
                        from models.models import UpdateCustomFieldDTO

                        self.custom_field_service.update(
                            cf_id, UpdateCustomFieldDTO(name=n, value=v)
                        )
                        form_ids.add(cf_id)
                    else:
                        new_cf = self.custom_field_service.create(
                            CreateCustomFieldDTO(
                                name=n, value=v, account_id=self.account.id
                            )
                        )
                        form_ids.add(getattr(new_cf, "id", None))
            to_delete = existing_ids - form_ids
            for cf_id in to_delete:
                self.custom_field_service.delete(cf_id)
        else:
            new_account = CreateAccountDTO(
                title=title,
                user_name=user_name,
                password=password,
                url=url,
                notes=notes,
                expiration_date=expiration_date,
            )
            account = self.account_service.create(new_account)
            for name, value in self.custom_fields:
                n = name.text().strip()
                v = value.text().strip()
                if n:
                    self.custom_field_service.create(
                        CreateCustomFieldDTO(name=n, value=v, account_id=account.id)
                    )
        super().accept()


class PasswordGeneratorDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Generate Password")
        self.setFixedSize(300, 250)
        layout = QtWidgets.QVBoxLayout(self)
        self.length = QtWidgets.QSpinBox()
        self.length.setMinimum(1)
        self.length.setValue(12)
        self.use_digits = QtWidgets.QCheckBox("Use digits")
        self.use_digits.setChecked(True)
        self.use_uppercase = QtWidgets.QCheckBox("Use uppercase")
        self.use_uppercase.setChecked(True)
        self.use_special = QtWidgets.QCheckBox("Use special chars")
        self.use_special.setChecked(True)
        layout.addWidget(QtWidgets.QLabel("Length:"))
        layout.addWidget(self.length)
        layout.addWidget(self.use_digits)
        layout.addWidget(self.use_uppercase)
        layout.addWidget(self.use_special)
        self.result_line_edit = QtWidgets.QLineEdit()
        layout.addWidget(self.result_line_edit)
        btn = QtWidgets.QPushButton("Generate")
        btn.clicked.connect(self.generate)
        layout.addWidget(btn)
        ok_btn = QtWidgets.QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)

    def generate(self):
        try:
            pwd = generate_password(
                length=self.length.value(),
                use_digits=self.use_digits.isChecked(),
                use_uppercase=self.use_uppercase.isChecked(),
                use_special=self.use_special.isChecked(),
            )
            self.result_line_edit.setText(pwd)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))

    def get_password(self):
        return self.result_line_edit.text()


class EscCloseFilter(QtCore.QObject):
    def __init__(self, window):
        super().__init__()
        self.window = window

    def eventFilter(self, a0, a1):
        if (
            a1 is not None
            and a1.type() == QtCore.QEvent.Type.KeyPress
            and isinstance(a1, QtGui.QKeyEvent)
        ):
            key_event = a1
            if key_event.key() == QtCore.Qt.Key.Key_Escape:
                self.window.close()
                return True
        return False


def start_gui_view():
    app = QtWidgets.QApplication(sys.argv)
    app_icon = QtGui.QIcon("assets/icon.png")
    app.setWindowIcon(app_icon)
    if not check_if_db_exists():
        QtWidgets.QMessageBox.information(
            None,
            "No database found",
            "No database was found. A new, secure database will be created. The master password you are about to set will be used to encrypt all your data.",
        )
    salt = load_salt()
    if salt is None:
        salt = create_salt()
    # Encryption key dialog
    while True:
        dlg = MasterPasswordDialog()
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            master_password = dlg.get_key()
            encryption_key = str(derive_key(master_password, salt))
            if check_if_db_exists():
                if is_key_valid(encryption_key):
                    break
                else:
                    QtWidgets.QMessageBox.critical(
                        None,
                        "Error",
                        "Invalid master password. Please check your master password and try again.",
                    )
            else:
                break
        else:
            sys.exit(0)

    with get_db_session() as db_session:
        db = db_session
        Account, CustomField = create_database(encryption_key)
        account_service = AccountService(db, Account)
        custom_field_service = CustomFieldService(db, CustomField, Account)

    main = MainWindow(account_service, custom_field_service)
    main.show()

    # Add account if DB is empty
    if check_if_db_is_empty(account_service):
        QtWidgets.QMessageBox.information(
            main, "Info", "No accounts found. Please add an account."
        )
        main.add_account()

    app.installEventFilter(EscCloseFilter(main))
    main.installEventFilter(EscCloseFilter(main))

    sys.exit(app.exec())
