import sys
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from sqlalchemy_utils.types.encrypted.padding import InvalidPaddingError

from models.models import (
    CreateAccountDTO,
    CreateCustomFieldDTO,
    UpdateAccountDTO,
    UpdateCustomFieldDTO,
)
from services.account_service import AccountService
from services.custom_field_service import CustomFieldService
from utils.utils import (
    check_if_db_is_empty,
    check_password_strength,
    check_secret_key,
    create_database,
    generate_password,
    get_db_session,
)


# --- Dialog for entering the master password (encryption key) ---
def ask_for_encryption_key(parent):
    """
    Show a modal dialog to ask the user for the master password (encryption key).
    Returns:
        str: The entered master password.
    """
    key_window = tk.Toplevel(parent)
    key_window.title("Enter master password")
    key_window.geometry("400x200")
    key_window.grab_set()
    key_window.focus_set()

    ttk.Label(
        key_window, text="Please enter the master password:", font=("Arial", 12)
    ).pack(pady=10)
    key_entry = ttk.Entry(key_window, show="*", font=("Arial", 12))
    key_entry.pack(pady=10)
    key_entry.focus_set()

    show_password = [False]

    def toggle_password():
        if show_password[0]:
            key_entry.config(show="*")
            show_password[0] = False
            show_btn.config(text="Show password")
        else:
            key_entry.config(show="")
            show_password[0] = True
            show_btn.config(text="Hide password")

    show_btn = ttk.Button(key_window, text="Show password", command=toggle_password)
    show_btn.pack(pady=(0, 8))

    key = tk.StringVar()

    def submit_key(event=None):
        entered_key = key_entry.get()
        if entered_key.strip():
            key.set(entered_key)
            key_window.destroy()
        else:
            messagebox.showwarning("Warning", "Master password cannot be empty.")

    ttk.Button(key_window, text="Submit", command=submit_key).pack(pady=10)

    key_window.bind("<Return>", submit_key)

    parent.wait_window(key_window)
    return key.get()


# --- Main accounts table with filtering, context menu, and double-click edit ---
def display_accounts(
    table_frame,
    account_service: AccountService,
    custom_field_service: CustomFieldService,
    filter_title: str = "",
    filter_user_name: str = "",
    filter_url: str = "",
    sort_column: str = None,  # type: ignore
    sort_reverse: bool = False,
):
    """
    Display the accounts table with filtering and context menu.

    Args:
        table_frame: The parent frame for the table.
        account_service: Service for account operations.
        custom_field_service: Service for custom field operations.
        filter_title: Filter string for the Title column.
        filter_user_name: Filter string for the User name column.
        filter_url: Filter string for the URL column.

    Returns:
        ttk.Treeview: The accounts table widget.
    """

    # Remove previous widgets from the table frame
    for widget in table_frame.winfo_children():
        widget.destroy()

    columns = (
        "Id",
        "Title",
        "User name",
        "URL",
        "Notes",
        "Expiration date",
    )

    # --- Filtering section for Title, User name, and URL ---
    filter_frame = ttk.Frame(table_frame)
    filter_frame.pack(fill="x", padx=8, pady=(4, 0))

    ttk.Label(filter_frame, text="Title:").pack(side="left")
    filter_title_var = tk.StringVar(value=filter_title)
    filter_title_entry = ttk.Entry(
        filter_frame, textvariable=filter_title_var, width=14
    )
    filter_title_entry.pack(side="left", padx=(2, 8))

    ttk.Label(filter_frame, text="User name:").pack(side="left")
    filter_user_name_var = tk.StringVar(value=filter_user_name)
    filter_user_name_entry = ttk.Entry(
        filter_frame, textvariable=filter_user_name_var, width=14
    )
    filter_user_name_entry.pack(side="left", padx=(2, 8))

    ttk.Label(filter_frame, text="URL:").pack(side="left")
    filter_url_var = tk.StringVar(value=filter_url)
    filter_url_entry = ttk.Entry(filter_frame, textvariable=filter_url_var, width=14)
    filter_url_entry.pack(side="left", padx=(2, 8))

    if not filter_title and not filter_user_name and not filter_url:
        filter_title_entry.focus_set()

    last_focus = {"field": "title"}

    def set_last_focus(event, field_name):
        last_focus["field"] = field_name

    filter_title_entry.bind("<FocusIn>", lambda e: set_last_focus(e, "title"))
    filter_user_name_entry.bind("<FocusIn>", lambda e: set_last_focus(e, "user"))
    filter_url_entry.bind("<FocusIn>", lambda e: set_last_focus(e, "url"))

    def on_filter_change(*args):
        current_title = filter_title_var.get()
        current_user_name = filter_user_name_var.get()
        current_url = filter_url_var.get()
        cursor_title = filter_title_entry.index(tk.INSERT)
        cursor_user = filter_user_name_entry.index(tk.INSERT)
        cursor_url = filter_url_entry.index(tk.INSERT)
        display_accounts(
            table_frame,
            account_service,
            custom_field_service,
            current_title,
            current_user_name,
            current_url,
        )

        for widget in table_frame.winfo_children():
            if isinstance(widget, ttk.Frame):
                entries = [
                    child
                    for child in widget.winfo_children()
                    if isinstance(child, ttk.Entry)
                ]
                if len(entries) >= 3:
                    if last_focus["field"] == "title":
                        entries[0].focus_set()
                        try:
                            entries[0].icursor(cursor_title)
                        except Exception:
                            pass
                    elif last_focus["field"] == "user":
                        entries[1].focus_set()
                        try:
                            entries[1].icursor(cursor_user)
                        except Exception:
                            pass
                    elif last_focus["field"] == "url":
                        entries[2].focus_set()
                        try:
                            entries[2].icursor(cursor_url)
                        except Exception:
                            pass

    filter_title_var.trace_add("write", on_filter_change)
    filter_user_name_var.trace_add("write", on_filter_change)
    filter_url_var.trace_add("write", on_filter_change)

    def on_paste_event(event):

        event.widget.after(1, on_filter_change)

    for entry in (filter_title_entry, filter_user_name_entry, filter_url_entry):
        entry.bind("<<Paste>>", on_paste_event)
        entry.bind("<Control-v>", on_paste_event)
        entry.bind("<ButtonRelease-2>", on_paste_event)

    # --- Table setup (Treeview) ---
    frame = ttk.Frame(table_frame)
    frame.pack(fill="both", expand=True, padx=8, pady=8)

    tree = ttk.Treeview(frame, columns=columns, show="headings", height=12)
    for col in columns:
        tree.heading(col, text=col, command=lambda c=col: sort_by_column(c))
        tree.column(col, width=100, anchor="center")

    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")

    hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    tree.configure(xscrollcommand=hsb.set)
    hsb.pack(side="bottom", fill="x")

    accounts = account_service.get_all()
    if filter_title:
        accounts = [
            acc for acc in accounts if filter_title.lower() in (acc.title or "").lower()
        ]
    if filter_user_name:
        accounts = [
            acc
            for acc in accounts
            if filter_user_name.lower() in (acc.user_name or "").lower()
        ]
    if filter_url:
        accounts = [
            acc for acc in accounts if filter_url.lower() in (acc.url or "").lower()
        ]

    if sort_column:

        def get_attr(acc):
            # Map column name to attribute
            mapping = {
                "Id": "id",
                "Title": "title",
                "User name": "user_name",
                "URL": "url",
                "Notes": "notes",
                "Expiration date": "expiration_date",
            }
            attr = mapping.get(sort_column, sort_column)
            val = getattr(acc, attr, "")
            # For None values, sort as empty string
            return val if val is not None else ""

        accounts = sorted(accounts, key=get_attr, reverse=sort_reverse)

    for acc in accounts:
        tree.insert(
            "",
            "end",
            values=(
                acc.id,
                acc.title,
                acc.user_name,
                acc.url,
                acc.notes,
                acc.expiration_date,
            ),
        )
    tree.pack(fill="both", expand=True)

    def sort_by_column(col):
        if not hasattr(table_frame, "_sort_col"):
            table_frame._sort_col = None
            table_frame._sort_reverse = False
        if table_frame._sort_col == col:
            table_frame._sort_reverse = not table_frame._sort_reverse
        else:
            table_frame._sort_col = col
            table_frame._sort_reverse = False
        display_accounts(
            table_frame,
            account_service,
            custom_field_service,
            filter_title_var.get() if "filter_title_var" in locals() else "",
            filter_user_name_var.get() if "filter_user_name_var" in locals() else "",
            filter_url_var.get() if "filter_url_var" in locals() else "",
            sort_column=table_frame._sort_col,  # type: ignore
            sort_reverse=table_frame._sort_reverse,
        )

    context_menu = tk.Menu(tree, tearoff=0)

    # --- Add submenu for custom fields ---
    other_data_menu = tk.Menu(context_menu, tearoff=0)

    def on_copy_custom_field_value(cf_value):
        root = tree.winfo_toplevel()
        root.clipboard_clear()
        root.clipboard_append(cf_value)

    def on_add_account():

        root = tree.winfo_toplevel()
        add_account_gui(
            root,
            account_service,
            custom_field_service,
            lambda: display_accounts(
                table_frame, account_service, custom_field_service
            ),
        )

    def on_edit_account():
        sel = tree.selection()
        if sel:
            values = tree.item(sel[0])["values"]
            if values:
                account = account_service.get_by_id(values[0])

                account_data = {
                    "Id": account.id,
                    "Title": account.title,
                    "User name": account.user_name,
                    "Password": account.password,
                    "URL": account.url,
                    "Notes": account.notes,
                    "Expiration date": account.expiration_date,
                    "custom_fields": list(account.custom_fields),
                }
                root = tree.winfo_toplevel()
                edit_account_gui(
                    root,
                    account_service,
                    custom_field_service,
                    account_data,
                    lambda: display_accounts(
                        table_frame, account_service, custom_field_service
                    ),
                )
            else:
                messagebox.showwarning("Warning", "No account selected.")
        else:
            messagebox.showwarning("Warning", "No account selected.")

    def on_copy_username():
        sel = tree.selection()
        if sel:
            values = tree.item(sel[0])["values"]
            if values:
                root = tree.winfo_toplevel()
                root.clipboard_clear()
                root.clipboard_append(values[2])

    def on_copy_password():
        sel = tree.selection()
        if sel:
            values = tree.item(sel[0])["values"]
            if values:
                account = account_service.get_by_id(values[0])
                root = tree.winfo_toplevel()
                root.clipboard_clear()
                root.clipboard_append(account.password)

    def on_delete_account():
        sel = tree.selection()
        if sel:
            values = tree.item(sel[0])["values"]
            if values:
                confirm = messagebox.askyesno(
                    "Confirm", "Are you sure you want to delete this account?"
                )
                if confirm:
                    account_service.delete(values[0])
                    display_accounts(table_frame, account_service, custom_field_service)
        else:
            messagebox.showwarning("Warning", "No account selected.")

    context_menu.add_command(label="Copy user name", command=on_copy_username)
    context_menu.add_command(label="Copy password", command=on_copy_password)
    context_menu.add_command(label="Add new account", command=on_add_account)
    context_menu.add_command(label="Edit account", command=on_edit_account)
    context_menu.add_command(label="Delete account", command=on_delete_account)
    # Add placeholder for custom fields submenu
    context_menu.add_cascade(label="Other data", menu=other_data_menu)

    def show_context_menu(event):

        row_id = tree.identify_row(event.y)
        if row_id:
            tree.selection_set(row_id)

        # --- Custom fields submenu dynamic update ---
        other_data_menu.delete(0, "end")
        sel = tree.selection()
        has_custom_fields = False
        if sel:
            values = tree.item(sel[0])["values"]
            if values:
                account = account_service.get_by_id(values[0])
                custom_fields = getattr(account, "custom_fields", [])
                if custom_fields:
                    has_custom_fields = True
                    for cf in custom_fields:
                        cf_name = getattr(cf, "name", None) or (
                            cf.get("name") if isinstance(cf, dict) else ""
                        )
                        cf_value = getattr(cf, "value", None) or (
                            cf.get("value") if isinstance(cf, dict) else ""
                        )
                        if cf_name:
                            other_data_menu.add_command(
                                label=f'Copy "{cf_name}" value',
                                command=lambda v=cf_value: on_copy_custom_field_value(
                                    v
                                ),
                            )
                else:
                    other_data_menu.add_command(
                        label="No custom fields", state="disabled"
                    )
            else:
                other_data_menu.add_command(label="No custom fields", state="disabled")
        else:
            other_data_menu.add_command(label="No custom fields", state="disabled")

        # --- Enable or disable menu items based on selection and custom fields ---
        if tree.selection():
            context_menu.entryconfig("Edit account", state="normal")
            context_menu.entryconfig("Copy user name", state="normal")
            context_menu.entryconfig("Copy password", state="normal")
            context_menu.entryconfig("Delete account", state="normal")
            # Enable "Other data" only if custom fields exist
            if has_custom_fields:
                context_menu.entryconfig("Other data", state="normal")
            else:
                context_menu.entryconfig("Other data", state="disabled")
        else:
            context_menu.entryconfig("Edit account", state="disabled")
            context_menu.entryconfig("Copy user name", state="disabled")
            context_menu.entryconfig("Copy password", state="disabled")
            context_menu.entryconfig("Delete account", state="disabled")
            context_menu.entryconfig("Other data", state="disabled")
        context_menu.tk_popup(event.x_root, event.y_root)

    tree.bind("<Button-3>", show_context_menu)

    # --- Double-click row to edit account ---
    def on_double_click(event):
        item = tree.identify_row(event.y)
        if item:
            tree.selection_set(item)
            values = tree.item(item)["values"]
            if values:
                account = account_service.get_by_id(values[0])
                account_data = {
                    "Id": account.id,
                    "Title": account.title,
                    "User name": account.user_name,
                    "Password": account.password,
                    "URL": account.url,
                    "Notes": account.notes,
                    "Expiration date": account.expiration_date,
                    "custom_fields": list(account.custom_fields),
                }
                root = tree.winfo_toplevel()
                edit_account_gui(
                    root,
                    account_service,
                    custom_field_service,
                    account_data,
                    lambda: display_accounts(
                        table_frame, account_service, custom_field_service
                    ),
                )

    tree.bind("<Double-1>", on_double_click)
    return tree


# --- Dialog for adding a new account (with custom fields and password generator) ---
def add_account_gui(
    root,
    account_service: AccountService,
    custom_field_service: CustomFieldService,
    refresh_callback,
):
    """
    Open a modal window for adding a new account.

    Args:
        root: The root Tk window.
        account_service: Service for account operations.
        custom_field_service: Service for custom field operations.
        refresh_callback: Function to call after successful addition.
    """
    add_window = tk.Toplevel(root)
    add_window.title("Add New Account")
    add_window.geometry("480x800")
    add_window.grab_set()
    add_window.focus_set()

    ttk.Label(
        add_window,
        text='Fields marked with "*" are required.',
        font=("Arial", 10, "italic"),
    ).pack(pady=(10, 5))

    fields = [
        ("Title*", tk.StringVar()),
        ("User name*", tk.StringVar()),
        ("Password*", tk.StringVar()),
        ("URL", tk.StringVar()),
        ("Notes", tk.StringVar()),
        ("Expiration date (DD-MM-YYYY)", tk.StringVar()),
    ]

    entries = []
    show_password = [False]
    password_strength_label = None  # for later reference

    for idx, (label, var) in enumerate(fields):
        ttk.Label(add_window, text=label + ":").pack(pady=2)
        if label.startswith("Notes"):
            notes_text = tk.Text(
                add_window, font=("TkFixedFont", 9), height=6, width=40, wrap="word"
            )
            notes_text.pack(pady=2)
            entries.append(notes_text)
        else:
            entry = ttk.Entry(
                add_window, textvariable=var, show="*" if "Password" in label else ""
            )
            entry.pack(pady=2)
            entries.append(entry)
            if label == "Password*":
                password_entry = entry

                def toggle_password():
                    if show_password[0]:
                        password_entry.config(show="*")
                        show_password[0] = False
                        show_btn.config(text="Show password")
                    else:
                        password_entry.config(show="")
                        show_password[0] = True
                        show_btn.config(text="Hide password")

                show_btn = ttk.Button(
                    add_window, text="Show password", command=toggle_password
                )
                show_btn.pack(pady=(0, 4))

                password_strength_label = ttk.Label(
                    add_window, text="Password strength: "
                )
                password_strength_label.pack(pady=2)

                def update_password_strength(*args):
                    password = fields[2][1].get()
                    strength = check_password_strength(password)
                    password_strength_label.config(  # type: ignore
                        text=f"Password strength: {strength}"
                    )

                # Ensure trace is set only once and updates live
                fields[2][1].trace_add("write", update_password_strength)
                update_password_strength()

                def open_generate_password_window():
                    gen_win = tk.Toplevel(add_window)
                    gen_win.title("Generate Password")
                    gen_win.geometry("300x250")
                    gen_win.grab_set()
                    gen_win.focus_set()

                    length_var = tk.IntVar(value=12)
                    use_digits = tk.BooleanVar(value=True)
                    use_uppercase = tk.BooleanVar(value=True)
                    use_special = tk.BooleanVar(value=True)

                    ttk.Label(gen_win, text="Length:").pack()
                    ttk.Entry(gen_win, textvariable=length_var).pack()

                    ttk.Checkbutton(
                        gen_win, text="Use digits", variable=use_digits
                    ).pack()
                    ttk.Checkbutton(
                        gen_win, text="Use uppercase", variable=use_uppercase
                    ).pack()
                    ttk.Checkbutton(
                        gen_win, text="Use special chars", variable=use_special
                    ).pack()

                    def generate_and_set(event=None):
                        try:
                            pwd = generate_password(
                                length=length_var.get(),
                                use_digits=use_digits.get(),
                                use_uppercase=use_uppercase.get(),
                                use_special=use_special.get(),
                            )
                            fields[2][1].set(pwd)
                            gen_win.destroy()
                            add_window.grab_set()
                            add_window.focus_set()
                        except Exception as e:
                            messagebox.showerror("Error", str(e))
                            gen_win.grab_set()
                            gen_win.focus_set()

                    ttk.Button(gen_win, text="Generate", command=generate_and_set).pack(
                        pady=10
                    )
                    gen_win.bind("<Return>", generate_and_set)

                ttk.Button(
                    add_window,
                    text="Generate password",
                    command=open_generate_password_window,
                ).pack(pady=5)

    custom_fields_label = ttk.Label(
        add_window, text="Custom fields", font=("Arial", 10, "bold")
    )
    custom_fields_label.pack(pady=(10, 0))

    custom_fields = []

    def add_custom_field_row():
        row_frame = ttk.Frame(custom_fields_frame)
        row_frame.pack(fill="x", pady=2)
        name_var = tk.StringVar()
        value_var = tk.StringVar()
        ttk.Entry(row_frame, textvariable=name_var, width=15).pack(side="left", padx=2)
        ttk.Entry(row_frame, textvariable=value_var, width=25).pack(side="left", padx=2)

        def remove_row():
            custom_fields.remove((name_var, value_var))
            row_frame.destroy()
            canvas.configure(scrollregion=canvas.bbox("all"))

        ttk.Button(row_frame, text="Remove", command=remove_row).pack(
            side="left", padx=2
        )
        custom_fields.append((name_var, value_var))
        canvas.configure(scrollregion=canvas.bbox("all"))

    ttk.Button(add_window, text="Add custom field", command=add_custom_field_row).pack(
        pady=(2, 6)
    )

    custom_fields_outer_frame = ttk.Frame(add_window)
    custom_fields_outer_frame.pack(fill="x", padx=10, pady=(0, 2))

    canvas = tk.Canvas(custom_fields_outer_frame, height=100)
    canvas.pack(side="left", fill="x", expand=True)

    scrollbar = ttk.Scrollbar(
        custom_fields_outer_frame, orient="vertical", command=canvas.yview
    )
    scrollbar.pack(side="right", fill="y")

    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.config(width=320)

    def on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    custom_fields_frame = ttk.Frame(canvas)
    canvas.create_window((0, 0), window=custom_fields_frame, anchor="nw")

    custom_fields_frame.bind("<Configure>", on_frame_configure)

    def _on_mousewheel(event):
        if event.delta:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        else:
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)
    canvas.bind_all("<Button-4>", _on_mousewheel)
    canvas.bind_all("<Button-5>", _on_mousewheel)

    custom_fields = []

    button_frame = ttk.Frame(add_window)
    button_frame.pack(pady=4)

    ttk.Button(button_frame, text="Submit", command=lambda: submit()).pack(
        side="left", padx=5, pady=10
    )

    def submit(event=None):
        title = fields[0][1].get()
        user_name = fields[1][1].get()
        password = fields[2][1].get()
        url = fields[3][1].get()
        notes = (
            entries[4].get("1.0", "end").strip()
            if hasattr(entries[4], "get")
            else fields[4][1].get()
        )
        expiration_date_str = fields[5][1].get()
        expiration_date = None
        if expiration_date_str:
            try:
                expiration_date = datetime.strptime(expiration_date_str, "%d-%m-%Y")
            except ValueError:
                messagebox.showerror("Error", "Invalid date format. Use DD-MM-YYYY.")
                return
        if not title or not user_name or not password:
            messagebox.showerror("Error", "Title, User name and Password are required.")
            add_window.grab_set()
            add_window.focus_set()
            return
        new_account = CreateAccountDTO(
            title=title,
            user_name=user_name,
            password=password,
            url=url,
            notes=notes,
            expiration_date=expiration_date,
        )
        account = account_service.create(new_account)

        for name_var, value_var in custom_fields:
            name = name_var.get().strip()
            value = value_var.get().strip()
            if name:
                custom_field_service.create(
                    CreateCustomFieldDTO(name=name, value=value, account_id=account.id)
                )

        messagebox.showinfo("Success", "Account added successfully!")
        add_window.destroy()
        refresh_callback()

    add_window.bind("<Return>", submit)


# --- Dialog for editing an existing account (with custom fields and password generator) ---
def edit_account_gui(
    root,
    account_service: AccountService,
    custom_field_service: CustomFieldService,
    account_data,
    refresh_callback,
):
    """
    Open a modal window for editing an existing account.

    Args:
        root: The root Tk window.
        account_service: Service for account operations.
        custom_field_service: Service for custom field operations.
        account_data: Dictionary with account data to edit.
        refresh_callback: Function to call after successful update.
    """
    edit_window = tk.Toplevel(root)
    edit_window.title("Edit Account")
    edit_window.geometry("480x800")
    edit_window.grab_set()
    edit_window.focus_set()

    ttk.Label(
        edit_window,
        text='Fields marked with "*" are required.',
        font=("Arial", 10, "italic"),
    ).pack(pady=(10, 5))

    expiration_date_value = ""
    try:
        if account_data["Expiration date"]:
            if isinstance(account_data["Expiration date"], datetime):
                expiration_date_value = account_data["Expiration date"].strftime(
                    "%d-%m-%Y"
                )
            else:
                expiration_date_value = datetime.strptime(
                    str(account_data["Expiration date"]), "%Y-%m-%d"
                ).strftime("%d-%m-%Y")
    except Exception:
        expiration_date_value = ""

    fields = [
        ("Title*", tk.StringVar(value=account_data["Title"])),
        ("User name*", tk.StringVar(value=account_data["User name"])),
        ("Password*", tk.StringVar(value=account_data["Password"])),
        ("URL", tk.StringVar(value=account_data["URL"])),
        ("Notes", tk.StringVar(value=account_data["Notes"])),
        (
            "Expiration date (DD-MM-YYYY)",
            tk.StringVar(value=expiration_date_value),
        ),
    ]

    entries = []
    show_password = [False]
    password_strength_label = None  # for later reference

    for idx, (label, var) in enumerate(fields):
        ttk.Label(edit_window, text=label + ":").pack(pady=2)
        if label.startswith("Notes"):
            notes_text = tk.Text(
                edit_window, font=("TkFixedFont", 9), height=6, width=40, wrap="word"
            )
            notes_text.insert("1.0", var.get())
            notes_text.pack(pady=2)
            entries.append(notes_text)
        else:
            entry = ttk.Entry(
                edit_window,
                textvariable=var,
                show="*" if "Password" in label else "",
            )
            entry.pack(pady=2)
            entries.append(entry)
            if label == "Password*":
                password_entry = entry

                def toggle_password():
                    if show_password[0]:
                        password_entry.config(show="*")
                        show_password[0] = False
                        show_btn.config(text="Show password")
                    else:
                        password_entry.config(show="")
                        show_password[0] = True
                        show_btn.config(text="Hide password")

                show_btn = ttk.Button(
                    edit_window,
                    text="Show password",
                    command=toggle_password,
                )
                show_btn.pack(pady=(0, 4))

                password_strength_label = ttk.Label(
                    edit_window, text="Password strength: "
                )
                password_strength_label.pack(pady=2)

                def update_password_strength(*args):
                    password = fields[2][1].get()
                    strength = check_password_strength(password)
                    password_strength_label.config(  # type: ignore
                        text=f"Password strength: {strength}"
                    )

                fields[2][1].trace_add("write", update_password_strength)
                update_password_strength()

                def open_generate_password_window():
                    gen_win = tk.Toplevel(edit_window)
                    gen_win.title("Generate Password")
                    gen_win.geometry("300x250")
                    gen_win.grab_set()
                    gen_win.focus_set()

                    length_var = tk.IntVar(value=12)
                    use_digits = tk.BooleanVar(value=True)
                    use_uppercase = tk.BooleanVar(value=True)
                    use_special = tk.BooleanVar(value=True)

                    ttk.Label(gen_win, text="Length:").pack()
                    ttk.Entry(gen_win, textvariable=length_var).pack()

                    ttk.Checkbutton(
                        gen_win, text="Use digits", variable=use_digits
                    ).pack()
                    ttk.Checkbutton(
                        gen_win, text="Use uppercase", variable=use_uppercase
                    ).pack()
                    ttk.Checkbutton(
                        gen_win, text="Use special chars", variable=use_special
                    ).pack()

                    def generate_and_set(event=None):
                        try:
                            pwd = generate_password(
                                length=length_var.get(),
                                use_digits=use_digits.get(),
                                use_uppercase=use_uppercase.get(),
                                use_special=use_special.get(),
                            )
                            fields[2][1].set(pwd)
                            gen_win.destroy()
                            edit_window.grab_set()
                            edit_window.focus_set()
                        except Exception as e:
                            messagebox.showerror("Error", str(e))
                            gen_win.grab_set()
                            gen_win.focus_set()

                    ttk.Button(gen_win, text="Generate", command=generate_and_set).pack(
                        pady=10
                    )
                    gen_win.bind("<Return>", generate_and_set)

                ttk.Button(
                    edit_window,
                    text="Generate password",
                    command=open_generate_password_window,
                ).pack(pady=5)

    custom_fields_label = ttk.Label(
        edit_window, text="Custom fields", font=("Arial", 10, "bold")
    )
    custom_fields_label.pack(pady=(10, 0))

    def add_custom_field_row():
        row_frame = ttk.Frame(custom_fields_frame)
        row_frame.pack(fill="x", pady=2)
        name_var = tk.StringVar()
        value_var = tk.StringVar()

        def remove_row():
            custom_fields.remove((name_var, value_var, None))
            row_frame.destroy()
            canvas.configure(scrollregion=canvas.bbox("all"))

        ttk.Entry(row_frame, textvariable=name_var, width=15).pack(side="left", padx=2)
        ttk.Entry(row_frame, textvariable=value_var, width=25).pack(side="left", padx=2)
        ttk.Button(row_frame, text="Remove", command=remove_row).pack(
            side="left", padx=2
        )
        custom_fields.append((name_var, value_var, None))
        canvas.configure(scrollregion=canvas.bbox("all"))

    ttk.Button(edit_window, text="Add custom field", command=add_custom_field_row).pack(
        pady=(2, 6)
    )

    custom_fields_outer_frame = ttk.Frame(edit_window)
    custom_fields_outer_frame.pack(fill="x", padx=10, pady=(0, 2))

    canvas = tk.Canvas(custom_fields_outer_frame, height=100)
    canvas.pack(side="left", fill="x", expand=True)

    scrollbar = ttk.Scrollbar(
        custom_fields_outer_frame, orient="vertical", command=canvas.yview
    )
    scrollbar.pack(side="right", fill="y")

    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.config(width=320)

    def on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    custom_fields_frame = ttk.Frame(canvas)
    canvas.create_window((0, 0), window=custom_fields_frame, anchor="nw")

    custom_fields_frame.bind("<Configure>", on_frame_configure)

    def _on_mousewheel(event):
        if event.delta:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        else:
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)
    canvas.bind_all("<Button-4>", _on_mousewheel)
    canvas.bind_all("<Button-5>", _on_mousewheel)

    custom_fields = []

    existing_custom_fields = []
    if "custom_fields" in account_data and account_data["custom_fields"]:
        existing_custom_fields = account_data["custom_fields"]

    for cf in existing_custom_fields:
        row_frame = ttk.Frame(custom_fields_frame)
        row_frame.pack(fill="x", pady=2)
        name = getattr(cf, "name", None) if hasattr(cf, "name") else cf.get("name", "")
        if not name:
            name = cf.get("name", "")
        value = (
            getattr(cf, "value", None) if hasattr(cf, "value") else cf.get("value", "")
        )
        if not value:
            value = cf.get("value", "")
        cf_id = getattr(cf, "id", None) if hasattr(cf, "id") else cf.get("id", None)
        name_var = tk.StringVar(value=name)
        value_var = tk.StringVar(value=value)

        def make_remove_row(row, pair, cf_id):
            def remove_row():
                if cf_id is not None:
                    custom_field_service.delete(cf_id)
                custom_fields.remove(pair)
                row.destroy()
                canvas.configure(scrollregion=canvas.bbox("all"))

            return remove_row

        ttk.Entry(row_frame, textvariable=name_var, width=15).pack(side="left", padx=2)
        ttk.Entry(row_frame, textvariable=value_var, width=25).pack(side="left", padx=2)
        pair = (name_var, value_var, cf_id)
        ttk.Button(
            row_frame, text="Remove", command=make_remove_row(row_frame, pair, cf_id)
        ).pack(side="left", padx=2)
        custom_fields.append(pair)

    button_frame = ttk.Frame(edit_window)
    button_frame.pack(pady=4)

    ttk.Button(button_frame, text="Save", command=lambda: submit()).pack(
        side="left", padx=5, pady=10
    )

    def submit(event=None):
        title = fields[0][1].get()
        user_name = fields[1][1].get()
        password = fields[2][1].get()
        url = fields[3][1].get()
        notes = entries[4].get("1.0", "end").strip()
        expiration_date_str = fields[5][1].get()
        expiration_date = None
        if expiration_date_str:
            try:
                expiration_date = datetime.strptime(expiration_date_str, "%d-%m-%Y")
            except ValueError:
                messagebox.showerror("Error", "Invalid date format. Use DD-MM-YYYY.")
                return
        if not title or not user_name or not password:
            messagebox.showerror("Error", "Title, User name and Password are required.")
            edit_window.grab_set()
            edit_window.focus_set()
            return
        update_account_dto = UpdateAccountDTO(
            title=title,
            user_name=user_name,
            password=password,
            url=url,
            notes=notes,
            expiration_date=expiration_date,
        )
        account_service.update(account_data["Id"], update_account_dto)

        current_custom_fields = []
        if "custom_fields" in account_data and account_data["custom_fields"]:
            current_custom_fields = account_data["custom_fields"]

        for name_var, value_var, cf_id in custom_fields:
            name = name_var.get().strip()
            value = value_var.get().strip()
            if name:
                if cf_id:
                    custom_field_service.update(
                        cf_id, UpdateCustomFieldDTO(name=name, value=value)
                    )
                else:
                    custom_field_service.create(
                        CreateCustomFieldDTO(
                            name=name, value=value, account_id=account_data["Id"]
                        )
                    )

        existing_ids = set()
        for cf in current_custom_fields:
            if hasattr(cf, "id"):
                existing_ids.add(cf.id)
            elif isinstance(cf, dict) and "id" in cf:
                existing_ids.add(cf["id"])
        form_ids = {cf_id for _, _, cf_id in custom_fields if cf_id}
        to_delete = existing_ids - form_ids
        for cf_id in to_delete:
            custom_field_service.delete(cf_id)

        messagebox.showinfo("Success", "Account updated successfully!")
        edit_window.destroy()
        refresh_callback()

    edit_window.bind("<Return>", submit)


# --- Main GUI entry point and application loop ---
def start_gui_view():
    """
    Entry point for the Password Manager GUI.
    Handles:
    - Encryption key prompt
    - Main window and layout
    - Service and database setup
    - Table and button setup
    - Button actions for add/edit/delete
    - Application close confirmation
    """
    root = tk.Tk()
    root.withdraw()

    import tkinter.font as tkfont

    for font_name in (
        "TkDefaultFont",
        "TkTextFont",
        "TkFixedFont",
        "TkHeadingFont",
        "TkMenuFont",
    ):
        f = tkfont.nametofont(font_name)
        f.configure(size=f.cget("size") + 2)

    try:
        icon = tk.PhotoImage(file="assets/icon.png")
        root.iconphoto(True, icon)
    except Exception as e:
        messagebox.showwarning("Warning", f"Could not load icon: {e}")

    encryption_key = ask_for_encryption_key(root)
    if not encryption_key:
        messagebox.showerror(
            "Error", "Encryption key is required to start the application."
        )
        root.destroy()
        return

    root.deiconify()
    root.title("Password Manager")
    root.geometry("740x400")
    try:
        with get_db_session() as db_session:
            db = db_session
            Account, CustomField = create_database(encryption_key)

        account_service = AccountService(db, Account)
        custom_field_service = CustomFieldService(db, CustomField, Account)
        check_secret_key(account_service)
    except InvalidPaddingError:
        messagebox.showwarning("Invalid secret key", "Please provide a valid key.")
        sys.exit(0)

    main_frame = ttk.Frame(root)
    main_frame.pack(fill="both", expand=True)

    table_frame = ttk.Frame(main_frame)
    table_frame.pack(fill="both", expand=True, pady=0, padx=0)

    button_frame = ttk.Frame(main_frame)
    button_frame.pack(pady=(0, 20))

    tree = display_accounts(
        table_frame, account_service, custom_field_service, "", "", ""
    )

    def refresh_accounts():
        nonlocal tree

        filter_title = filter_user_name = filter_url = ""
        for widget in table_frame.winfo_children():
            if isinstance(widget, ttk.Frame):
                entries = [
                    child
                    for child in widget.winfo_children()
                    if isinstance(child, ttk.Entry)
                ]
                if len(entries) >= 3:
                    filter_title = entries[0].get()
                    filter_user_name = entries[1].get()
                    filter_url = entries[2].get()
        tree = display_accounts(
            table_frame,
            account_service,
            custom_field_service,
            filter_title,
            filter_user_name,
            filter_url,
        )

    def on_edit_account_button():
        sel = tree.selection()
        if sel:
            values = tree.item(sel[0])["values"]
            if values:
                account = account_service.get_by_id(values[0])

                account_data = {
                    "Id": account.id,
                    "Title": account.title,
                    "User name": account.user_name,
                    "Password": account.password,
                    "URL": account.url,
                    "Notes": account.notes,
                    "Expiration date": account.expiration_date,
                    "custom_fields": list(account.custom_fields),
                }
                edit_account_gui(
                    root,
                    account_service,
                    custom_field_service,
                    account_data,
                    refresh_accounts,
                )
            else:
                messagebox.showwarning("Warning", "No account selected.")
        else:
            messagebox.showwarning("Warning", "No account selected.")

    def on_delete_account_button():
        sel = tree.selection()
        if sel:
            values = tree.item(sel[0])["values"]
            if values:
                confirm = messagebox.askyesno(
                    "Confirm", "Are you sure you want to delete this account?"
                )
                if confirm:
                    account_service.delete(values[0])
                    refresh_accounts()
        else:
            messagebox.showwarning("Warning", "No account selected.")

    ttk.Button(
        button_frame,
        text="Add Account",
        command=lambda: add_account_gui(
            root, account_service, custom_field_service, refresh_accounts
        ),
    ).pack(side="left", padx=10)

    ttk.Button(
        button_frame,
        text="Edit",
        command=on_edit_account_button,
    ).pack(side="left", padx=10)

    ttk.Button(
        button_frame,
        text="Delete",
        command=on_delete_account_button,
    ).pack(side="left", padx=10)

    def on_close():
        if messagebox.askokcancel(
            "Exit", "Are you sure you want to exit the application?"
        ):
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    if check_if_db_is_empty(account_service):
        messagebox.showinfo("Info", "No accounts found. Please add an account.")
        add_account_gui(root, account_service, custom_field_service, refresh_accounts)

    root.mainloop()
