import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

DB_NAME = "cafe.db"


def get_connection():
    connection = sqlite3.connect(DB_NAME)
    connection.row_factory = sqlite3.Row
    return connection


def create_tables():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT UNIQUE,
        balance INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cafe_tables (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        number TEXT UNIQUE NOT NULL,
        capacity INTEGER NOT NULL,
        price_per_hour INTEGER NOT NULL,
        status TEXT DEFAULT 'available'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reservations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        table_id INTEGER NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        cost INTEGER DEFAULT 0,
        status TEXT DEFAULT 'reserved',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(customer_id) REFERENCES customers(id),
        FOREIGN KEY(table_id) REFERENCES cafe_tables(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        reservation_id INTEGER,
        amount INTEGER NOT NULL,
        type TEXT NOT NULL,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(customer_id) REFERENCES customers(id),
        FOREIGN KEY(reservation_id) REFERENCES reservations(id)
    )
    """)

    connection.commit()
    connection.close()


# customer

def add_customer(name, phone):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
            """ 
            INSERT INTO customers
            (name, phone, balance)
            VALUES (?, ?, ?)
            """,
            (
                name,
                phone,
                0
            )
        )
    connection.commit()
    connection.close()
    return True


def get_customers():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM customers")
    rows = cursor.fetchall()
    connection.close()

    result = []
    for row in rows:
        result.append(dict(row))

    return result


def get_customer_by_id(customer_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM customers WHERE id=?", (customer_id,))
    row = cursor.fetchone()
    connection.close()

    if row:
        return dict(row)
    else:
        return None


def update_customer(customer_id, name, phone, balance):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "UPDATE customers SET name=?, phone=?, balance=? WHERE id=?",
        (name, phone, balance, customer_id)
    )
    connection.commit()
    connection.close()
    return True


def delete_customer(customer_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM customers WHERE id=?", (customer_id,))
    connection.commit()
    connection.close()
    return True


def get_customer_details(customer_id):
    return {
        "customer": get_customer_by_id(customer_id),
        "reservations": get_reservations_by_customer(customer_id),
        "transactions": get_transactions_by_customer(customer_id)
    }


# table

def add_table(number, capacity, price_per_hour):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO cafe_tables (number, capacity, price_per_hour, status) VALUES (?, ?, ?, ?)",
        (number, capacity, price_per_hour, "available")
    )
    conn.commit()
    conn.close()
    return True


def get_tables():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM cafe_tables")
    rows = cur.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        result.append(dict(row))

    return result


def get_table_by_id(table_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM cafe_tables WHERE id=?", (table_id,))
    row = cur.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    else:
        return None


def get_table_status(table_id):
    reservations = get_reservations_by_table(table_id)

    for r in reservations:
        if r["status"] == "playing":
            return "playing"

    for r in reservations:
        if r["status"] == "reserved":
            return "reserved"

    return "available"


def update_table(table_id, number, capacity, price_per_hour):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE cafe_tables SET number=?, capacity=?, price_per_hour=? WHERE id=?",
        (number, capacity, price_per_hour, table_id)
    )
    conn.commit()
    conn.close()
    return True


def delete_table(table_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM cafe_tables WHERE id=?", (table_id,))
    conn.commit()
    conn.close()
    return True


# reservation

def calculate_cost(table_id, start_time, end_time):
    table = get_table_by_id(table_id)

    start = datetime.strptime(start_time, "%H:%M")
    end = datetime.strptime(end_time, "%H:%M")

    duration = (end - start).seconds / 3600
    return int(duration * table["price_per_hour"])


def check_table_available(table_id, start_time, end_time):
    reservations = get_reservations_by_table(table_id)

    for r in reservations:
        if r["status"] == "reserved" or r["status"] == "playing":
            if start_time < r["end_time"] and end_time > r["start_time"]:
                return False
    return True


def create_reservation(customer_id, table_id, start_time, end_time):
    if not check_table_available(table_id, start_time, end_time):
        return False

    cost = calculate_cost(table_id, start_time, end_time)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO reservations
        (customer_id, table_id, start_time, end_time, cost, status)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (customer_id, table_id, start_time, end_time, cost, "reserved")
    )
    conn.commit()
    conn.close()

    customer = get_customer_by_id(customer_id)
    update_customer(customer_id, customer["name"], customer["phone"], customer["balance"] + cost)

    return True




def finish_game(reservation_id, customer_id, amount):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE reservations SET status=? WHERE id=?", ("finished", reservation_id))
    conn.commit()
    conn.close()

    add_transaction(customer_id, reservation_id, amount, "payment")


def cancel_reservation(reservation_id):
    reservation = get_reservation_by_id(reservation_id)
    if not reservation:
        return False

    customer = get_customer_by_id(reservation["customer_id"])
    new_balance = customer["balance"] - reservation["cost"]
    if new_balance < 0:
        new_balance = 0

    update_customer(customer["id"], customer["name"], customer["phone"], new_balance)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM reservations WHERE id=?", (reservation_id,))
    conn.commit()
    conn.close()

    return True


def get_reservation_by_id(reservation_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM reservations WHERE id=?", (reservation_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_reservations():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM reservations")
    rows = cur.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        result.append(dict(row))

    return result



def get_reservations_by_customer(customer_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM reservations WHERE customer_id=?", (customer_id,))
    rows = cur.fetchall()
    conn.close()
    
    result = []

    for row in rows:
        result.append(dict(row))

    return result


def get_reservations_by_table(table_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM reservations WHERE table_id=?", (table_id,))
    rows = cur.fetchall()
    conn.close()
    
    result = []

    for row in rows:
        result.append(dict(row))

    return result


# transaction

def add_transaction(customer_id, reservation_id, amount, type_):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO transactions (customer_id, reservation_id, amount, type) VALUES (?, ?, ?, ?)",
        (customer_id, reservation_id, amount, type_)
    )
    conn.commit()
    conn.close()


def create_payment(customer_id, reservation_id, amount):
    if amount <= 0:
        return False

    add_transaction(customer_id, reservation_id, amount, "payment")

    customer = get_customer_by_id(customer_id)
    new_balance = customer["balance"] - amount
    if new_balance < 0:
        new_balance = 0

    update_customer(customer_id, customer["name"], customer["phone"], new_balance)
    return True



def get_transactions_by_customer(customer_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM transactions WHERE customer_id=? ORDER BY date DESC", (customer_id,))
    rows = cur.fetchall()
    conn.close()
    
    result = []

    for row in rows:
        result.append(dict(row))

    return result


def get_all_transactions():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM transactions")
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_total_income():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT SUM(amount) FROM transactions WHERE type='payment'")
    result = cur.fetchone()
    conn.close()
    
    if result[0]:
        return result[0]
    else:
        return 0

# customer ui

def open_customer_window():
    win = tk.Toplevel()
    win.title("Customers")
    win.geometry("1000x700")

    selected_id = None

    form = tk.Frame(win)
    form.pack(pady=10)

    tk.Label(form, text="Name").grid(row=0, column=0)
    name_entry = tk.Entry(form)
    name_entry.grid(row=0, column=1)

    tk.Label(form, text="Phone").grid(row=1, column=0)
    phone_entry = tk.Entry(form)
    phone_entry.grid(row=1, column=1)

    columns = ("id", "name", "phone", "balance")
    table = ttk.Treeview(win, columns=columns, show="headings")
    for col in columns:
        table.heading(col, text=col)
    table.pack(fill="both", expand=True)

    def refresh():
        for row in table.get_children():
            table.delete(row)
        for c in get_customers():
            table.insert("", "end", values=(c["id"], c["name"], c["phone"], c["balance"]))

    def on_select(event):
        nonlocal selected_id
        sel = table.focus()
        if not sel:
            return

        values = table.item(sel)["values"]
        selected_id = values[0]

        name_entry.delete(0, tk.END)
        name_entry.insert(0, values[1])
        
        phone_entry.delete(0, tk.END)
        phone_entry.insert(0, values[2])

    def on_add():
        if add_customer(name_entry.get(), phone_entry.get()):
            messagebox.showinfo("Success", "Customer Added")
            refresh()

    def on_update():
        if not selected_id:
            return
        update_customer(selected_id, name_entry.get(), phone_entry.get(), 0)
        refresh()

    def on_delete():
        if not selected_id:
            return
        delete_customer(selected_id)
        refresh()

    def on_history():
        if not selected_id:
            return

        data = get_customer_details(selected_id)

        hist = tk.Toplevel()
        hist.title("Customer History")
        hist.geometry("500x400")

        tk.Label(hist, text="Reservations").pack()
        for r in data["reservations"]:
            tk.Label(hist, text=f"Reservation {r['id']}").pack()

        tk.Label(hist, text="Transactions").pack()
        for t in data["transactions"]:
            tk.Label(hist, text=f"{t['type']}: {t['amount']}").pack()

    tk.Button(form, text="Add", padx=40, command=on_add).grid(row=2, column=0, pady=5)
    tk.Button(form, text="Update", padx=40, command=on_update).grid(row=2, column=1, pady=5)
    tk.Button(form, text="Delete", padx=40, command=on_delete).grid(row=2, column=2, pady=5)
    tk.Button(form, text="History", padx=40, command=on_history).grid(row=2, column=3, pady=5)

    table.bind("<ButtonRelease-1>", on_select)

    refresh()


# table ui

def open_table_window():
    win = tk.Toplevel()
    win.title("Tables")
    win.geometry("1000x700")

    selected_id = None

    form = tk.Frame(win)
    form.pack(pady=10)

    tk.Label(form, text="Number").grid(row=0, column=0)
    number_entry = tk.Entry(form)
    number_entry.grid(row=0, column=1)

    tk.Label(form, text="Capacity").grid(row=1, column=0)
    capacity_entry = tk.Entry(form)
    capacity_entry.grid(row=1, column=1)

    tk.Label(form, text="Price/hour").grid(row=2, column=0)
    price_entry = tk.Entry(form)
    price_entry.grid(row=2, column=1)

    columns = ("id", "number", "capacity", "price", "status")
    table = ttk.Treeview(win, columns=columns, show="headings")
    for col in columns:
        table.heading(col, text=col)

    table.column("id", width=40)
    table.column("number", width=80)
    table.column("capacity", width=80)
    table.column("price", width=100)
    table.column("status", width=90)
    table.pack(fill="both", expand=True)

    def refresh():
        for row in table.get_children():
            table.delete(row)

        for t in get_tables():
            status = get_table_status(t["id"])
            table.insert("", "end", values=(t["id"], t["number"], t["capacity"], t["price_per_hour"], status))

    def on_select(event):
        nonlocal selected_id
        sel = table.focus()
        if not sel:
            return

        values = table.item(sel)["values"]
        selected_id = values[0]

        number_entry.delete(0, tk.END)
        number_entry.insert(0, values[1])

        capacity_entry.delete(0, tk.END)
        capacity_entry.insert(0, values[2])

        price_entry.delete(0, tk.END)
        price_entry.insert(0, values[3])

    def on_add():
        result = add_table(number_entry.get(), int(capacity_entry.get()), int(price_entry.get()))
        if result:
            messagebox.showinfo("Success", "Table Added")
            refresh()

    def on_update():
        if not selected_id:
            return 
        update_table(selected_id, number_entry.get(), int(capacity_entry.get()), int(price_entry.get()))
        refresh()

    def on_delete():
        if not selected_id:
            return
        delete_table(selected_id)
        refresh()

    tk.Button(form, text="Add", padx=40, command=on_add).grid(row=3, column=0, pady=5)
    tk.Button(form, text="Update", padx=40, command=on_update).grid(row=3, column=1, pady=5)
    tk.Button(form, text="Delete", padx=40, command=on_delete).grid(row=3, column=2, pady=5)

    table.bind("<ButtonRelease-1>", on_select)

    refresh()




def open_reservation_window():
    win = tk.Toplevel()
    win.title("Reservations")
    win.geometry("1000x700")

    selected_id = None

    form = tk.Frame(win)
    form.pack(pady=10)

    tk.Label(form, text="Customer").grid(row=0, column=0)
    customer_box = ttk.Combobox(form)
    customer_box.grid(row=0, column=1)

    tk.Label(form, text="Table").grid(row=1, column=0)
    table_box = ttk.Combobox(form)
    table_box.grid(row=1, column=1)

    tk.Label(form, text="Start").grid(row=2, column=0)
    start_entry = tk.Entry(form)
    start_entry.grid(row=2, column=1)

    tk.Label(form, text="End").grid(row=3, column=0)
    end_entry = tk.Entry(form)
    end_entry.grid(row=3, column=1)

    columns = ("id", "customer", "table", "start", "end", "cost", "status")
    tree = ttk.Treeview(win, columns=columns, show="headings")
    for col in columns:
        tree.heading(col, text=col)

    tree.column("id", width=40)
    tree.column("customer", width=80)
    tree.column("table", width=60)
    tree.column("start", width=80)
    tree.column("end", width=80)
    tree.column("cost", width=100)
    tree.column("status", width=80)
    tree.pack(fill="both", expand=True)

    def load_customer_list():
         customer_box["values"] = [f"{c['id']}-{c['name']}" for c in get_customers()]

    def load_table_list():
        table_box["values"] = [f"{t['id']}-{t['number']}" for t in get_tables()]

    def refresh():
        for item in tree.get_children():
            tree.delete(item)

        for r in get_reservations():
            tree.insert("", "end", values=(
                r["id"], r["customer_id"], r["table_id"],
                r["start_time"], r["end_time"], r["cost"], r["status"]
            ))

    def on_select(event):
        nonlocal selected_id
        sel = tree.focus()
        if sel:
            selected_id = tree.item(sel)["values"][0]

    def on_create():
        customer_id = customer_box.get().split("-")[0]

        print(customer_id)

        table_id = int(table_box.get().split("-")[0])

        result = create_reservation(customer_id, table_id, start_entry.get(), end_entry.get())

        if result:
            messagebox.showinfo("Success", "Reservation Created")
            refresh()
        else:
            messagebox.showerror("Error", "Table is not available")

    def on_finish():
        if not selected_id:
            return
        row = tree.item(tree.focus())["values"]
        finish_game(selected_id, row[1], row[5])
        refresh()

    def on_cancel():
        if not selected_id:
            return
        cancel_reservation(selected_id)
        refresh()

    tk.Button(form, text="Create Reservation", padx=30, command=on_create).grid(row=5, column=0, pady=5)
    tk.Button(form, text="Finish Game", padx=30, command=on_finish).grid(row=5, column=1, pady=5)
    tk.Button(form, text="Cancel", padx=30, command=on_cancel).grid(row=5, column=2, pady=5)

    tree.bind("<ButtonRelease-1>", on_select)

    load_customer_list()
    load_table_list()
    refresh()




def open_transaction_window():
    win = tk.Toplevel()
    win.title("Transactions")
    win.geometry("1000x700")

    form = tk.Frame(win)
    form.pack(pady=10)

    tk.Label(form, text="Customer").grid(row=0, column=0)
    customer_box = ttk.Combobox(form)
    customer_box.grid(row=0, column=1)

    tk.Label(form, text="Amount").grid(row=1, column=0)
    amount_entry = tk.Entry(form)
    amount_entry.grid(row=1, column=1)

    columns = ("id", "customer", "reservation", "amount", "type", "date")
    tree = ttk.Treeview(win, columns=columns, show="headings")
    for col in columns:
        tree.heading(col, text=col)
    tree.pack(fill="both", expand=True)

    

    def load_customer_list():
        customer_box["values"] = [c["name"] for c in get_customers()]


    def refresh():
        for item in tree.get_children():
            tree.delete(item)

        for t in get_all_transactions():
            tree.insert("", "end", values=(
                t["id"], t["customer_id"], t["reservation_id"], t["amount"], t["type"], t["date"]
            ))

    def on_payment():
        customer_map = {}
        customer_map.clear()
        for c in get_customers():
            customer_map[c["name"]] = c["id"]

        selected_name = customer_box.get()
        customer_id = customer_map[selected_name]
        amount = int(amount_entry.get())

        if create_payment(customer_id, None, amount):
            messagebox.showinfo("Success", "Payment Added")
            refresh()

    def on_income():
        income = get_total_income()
        messagebox.showinfo("Total Income", f"{income} ")

    tk.Button(form, text="Add Payment", padx=35, pady=2, command=on_payment).grid(row=2, column=0, pady=5)
    tk.Button(form, text="Income", padx=45, command=on_income).grid(row=2, column=1, pady=5)

    load_customer_list()
    refresh()



def main():
    create_tables()

    root = tk.Tk()
    root.title("Cafe Management")
    root.geometry("1400x800")

    tk.Label(root, text="Cafe Game Management", font=("Arial", 20)).pack(pady=20)

    tk.Button(root, text="Customers", width=20, command=open_customer_window).pack(pady=5)
    tk.Button(root, text="Tables", width=20, command=open_table_window).pack(pady=5)
    tk.Button(root, text="Reservations", width=20, command=open_reservation_window).pack(pady=5)
    tk.Button(root, text="Transactions", width=20, command=open_transaction_window).pack(pady=5)

    root.mainloop()


main()