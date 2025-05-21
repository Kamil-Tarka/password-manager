import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from models.models import CreateAccountDTO, CreateCustomFieldDTO, UpdateAccountDTO
from services.account_service import AccountService
from services.custom_field_service import CustomFieldService
from utils.utils import (
    check_password_strength,
    create_database,
    generate_password,
    get_db_session,
)


def ask_for_encryption_key(parent):
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

    key = tk.StringVar()

    def submit_key(event=None):  # Dodano `event=None` dla obsługi zdarzeń klawiatury
        entered_key = key_entry.get()
        if entered_key.strip():
            key.set(entered_key)
            key_window.destroy()
        else:
            messagebox.showwarning("Warning", "Master password cannot be empty.")

    # Przycisk do zatwierdzenia klucza
    ttk.Button(key_window, text="Submit", command=submit_key).pack(pady=10)

    # Powiązanie klawisza Enter z funkcją `submit_key`
    key_window.bind("<Return>", submit_key)

    parent.wait_window(key_window)
    return key.get()


def display_accounts(
    table_frame,
    account_service: AccountService,
    custom_field_service: CustomFieldService,
):
    # Usuwanie poprzednich widżetów tylko z ramki tabeli
    for widget in table_frame.winfo_children():
        widget.destroy()

    columns = (
        "Id",
        "Title",
        "User name",
        "Password",
        "URL",
        "Notes",
        "Expiration date",
    )

    frame = ttk.Frame(table_frame)
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    tree = ttk.Treeview(frame, columns=columns, show="headings")
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=120, anchor="center")

    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")

    hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    tree.configure(xscrollcommand=hsb.set)
    hsb.pack(side="bottom", fill="x")

    accounts = account_service.get_all()
    for acc in accounts:
        tree.insert(
            "",
            "end",
            values=(
                acc.id,
                acc.title,
                acc.user_name,
                "*" * len(acc.password),
                acc.url,
                acc.notes,
                acc.expiration_date,
            ),
        )
    tree.pack(fill="both", expand=True)

    # --- MENU KONTEKSTOWE ---
    context_menu = tk.Menu(tree, tearoff=0)

    # Funkcja refresh_callback musi być przekazana do display_accounts!
    def on_add_account():
        # root musi być przekazany do display_accounts lub pobrany przez .winfo_toplevel()
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
                account_data = {
                    "Id": values[0],
                    "Title": values[1],
                    "User name": values[2],
                    "Password": values[3],
                    "URL": values[4],
                    "Notes": values[5],
                    "Expiration date": values[6],
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

    context_menu.add_command(label="Add new account", command=on_add_account)
    context_menu.add_command(label="Edit account", command=on_edit_account)

    def show_context_menu(event):
        # Zaznacz wiersz pod kursorem, jeśli istnieje
        row_id = tree.identify_row(event.y)
        if row_id:
            tree.selection_set(row_id)
        # Ustaw stan opcji "Edit account"
        if tree.selection():
            context_menu.entryconfig("Edit account", state="normal")
        else:
            context_menu.entryconfig("Edit account", state="disabled")
        context_menu.tk_popup(event.x_root, event.y_root)

    tree.bind("<Button-3>", show_context_menu)
    return tree


def add_account_gui(
    root,
    account_service: AccountService,
    custom_field_service: CustomFieldService,
    refresh_callback,
):
    add_window = tk.Toplevel(root)
    add_window.title("Add New Account")
    add_window.geometry("400x500")
    add_window.grab_set()
    add_window.focus_set()

    # Dodaj informację o polach obowiązkowych
    ttk.Label(
        add_window,
        text='Fields marked with "*" are required.',
        # foreground="red",
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
    for label, var in fields:
        ttk.Label(add_window, text=label + ":").pack(pady=2)
        entry = ttk.Entry(
            add_window, textvariable=var, show="*" if "Password" in label else ""
        )
        entry.pack(pady=2)
        entries.append(entry)

    # --- Sekcja generowania hasła i siły hasła ---
    password_strength_label = ttk.Label(add_window, text="Password strength: ")
    password_strength_label.pack(pady=2)

    def update_password_strength(*args):
        password = fields[2][1].get()
        strength = check_password_strength(password)
        password_strength_label.config(text=f"Password strength: {strength}")

    fields[2][1].trace_add("write", update_password_strength)

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

        ttk.Checkbutton(gen_win, text="Use digits", variable=use_digits).pack()
        ttk.Checkbutton(gen_win, text="Use uppercase", variable=use_uppercase).pack()
        ttk.Checkbutton(gen_win, text="Use special chars", variable=use_special).pack()

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
                # return "break"
            except Exception as e:
                messagebox.showerror("Error", str(e))
                gen_win.grab_set()
                gen_win.focus_set()
                # return "break"

        ttk.Button(gen_win, text="Generate", command=generate_and_set).pack(pady=10)
        gen_win.bind("<Return>", generate_and_set)  # Enter generuje hasło

    ttk.Button(
        add_window, text="Generate password", command=open_generate_password_window
    ).pack(pady=5)
    # --- Koniec sekcji generowania hasła ---

    custom_fields = []

    custom_fields_frame = ttk.LabelFrame(add_window, text="Custom fields")
    custom_fields_frame.pack(fill="x", padx=10, pady=10)

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

        ttk.Button(row_frame, text="Remove", command=remove_row).pack(
            side="left", padx=2
        )
        custom_fields.append((name_var, value_var))

    ttk.Button(
        custom_fields_frame, text="Add custom field", command=add_custom_field_row
    ).pack(pady=2)

    # --- Koniec sekcji custom fields ---

    def submit(event=None):
        title = fields[0][1].get()
        user_name = fields[1][1].get()
        password = fields[2][1].get()
        url = fields[3][1].get()
        notes = fields[4][1].get()
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

        custom_fields_dto = []
        for name_var, value_var in custom_fields:
            name = name_var.get().strip()
            value = value_var.get().strip()
            if name:  # tylko jeśli podano nazwę
                custom_field_service.create(
                    CreateCustomFieldDTO(name=name, value=value, account_id=account.id)
                )

        messagebox.showinfo("Success", "Account added successfully!")
        add_window.destroy()
        refresh_callback()

    ttk.Button(add_window, text="Submit", command=submit).pack(pady=10)

    # Obsługa Enter dla całego okna formularza
    add_window.bind("<Return>", submit)


def edit_account_gui(
    root,
    account_service: AccountService,
    custom_field_service: CustomFieldService,
    account_data,
    refresh_callback,
):
    edit_window = tk.Toplevel(root)
    edit_window.title("Edit Account")
    edit_window.geometry("400x500")
    edit_window.grab_set()
    edit_window.focus_set()

    ttk.Label(
        edit_window,
        text='Fields marked with "*" are required.',
        font=("Arial", 10, "italic"),
    ).pack(pady=(10, 5))

    # Determine expiration date string
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
    for label, var in fields:
        ttk.Label(edit_window, text=label + ":").pack(pady=2)
        entry = ttk.Entry(
            edit_window, textvariable=var, show="*" if "Password" in label else ""
        )
        entry.pack(pady=2)
        entries.append(entry)

    # --- Sekcja generowania hasła i siły hasła ---
    password_strength_label = ttk.Label(edit_window, text="Password strength: ")
    password_strength_label.pack(pady=2)

    def update_password_strength(*args):
        password = fields[2][1].get()
        strength = check_password_strength(password)
        password_strength_label.config(text=f"Password strength: {strength}")

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

        ttk.Checkbutton(gen_win, text="Use digits", variable=use_digits).pack()
        ttk.Checkbutton(gen_win, text="Use uppercase", variable=use_uppercase).pack()
        ttk.Checkbutton(gen_win, text="Use special chars", variable=use_special).pack()

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

        ttk.Button(gen_win, text="Generate", command=generate_and_set).pack(pady=10)
        gen_win.bind("<Return>", generate_and_set)

    ttk.Button(
        edit_window, text="Generate password", command=open_generate_password_window
    ).pack(pady=5)
    # --- Koniec sekcji generowania hasła ---

    def submit(event=None):
        title = fields[0][1].get()
        user_name = fields[1][1].get()
        password = fields[2][1].get()
        url = fields[3][1].get()
        notes = fields[4][1].get()
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
        # Aktualizacja konta
        update_account_dto = UpdateAccountDTO(
            title=title,
            user_name=user_name,
            password=password,
            url=url,
            notes=notes,
            expiration_date=expiration_date,
        )
        account_service.update(account_data["Id"], update_account_dto)
        messagebox.showinfo("Success", "Account updated successfully!")
        edit_window.destroy()
        refresh_callback()

    ttk.Button(edit_window, text="Save", command=submit).pack(pady=10)
    edit_window.bind("<Return>", submit)


def start_gui_view():
    root = tk.Tk()
    root.withdraw()

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
    root.geometry("800x600")

    with get_db_session() as db_session:
        db = db_session
        Account, CustomField = create_database(encryption_key)

    account_service = AccountService(db, Account)
    custom_field_service = CustomFieldService(db, CustomField, Account)
    # Główna ramka
    main_frame = ttk.Frame(root)
    main_frame.pack(fill="both", expand=True)

    # Ramka na tabelę
    table_frame = ttk.Frame(main_frame)
    table_frame.pack(fill="both", expand=True, pady=0)

    # Ramka na przyciski
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(pady=(0, 20))

    tree = display_accounts(table_frame, account_service, custom_field_service)

    def refresh_accounts():
        nonlocal tree
        tree = display_accounts(table_frame, account_service, custom_field_service)

    def on_edit_account_button():
        sel = tree.selection()
        if sel:
            values = tree.item(sel[0])["values"]
            if values:
                account_data = {
                    "Id": values[0],
                    "Title": values[1],
                    "User name": values[2],
                    "Password": values[3],  # nie wyciągamy zamaskowanego hasła
                    "URL": values[4],
                    "Notes": values[5],
                    "Expiration date": values[6],
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

    ttk.Button(
        button_frame,
        text="Add Account",
        command=lambda: add_account_gui(
            root, account_service, custom_field_service, refresh_accounts
        ),
    ).pack()

    ttk.Button(
        button_frame,
        text="Edit",
        command=on_edit_account_button,
    ).pack(pady=5)

    root.mainloop()
