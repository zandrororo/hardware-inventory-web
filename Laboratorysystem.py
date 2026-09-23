#from tkinter import ttk, messagebox
import sqlite3
import bcrypt
import os
import logging
import csv
from datetime import datetime
import re

# ==========================================
# 0. CUSTOM STYLING COLOR PALETTE (DARK MODE)
# ==========================================
BG_COLOR = "#0D1117"
PANEL_BG = "#161B22"
TEXT_COLOR = "#C9D1D9"
ACCENT_BLUE = "#58A6FF"
ACCENT_GREEN = "#238636"
ACCENT_RED = "#DA3633"
ACCENT_YELLOW = "#E3B341"
ACCENT_PURPLE = "#A371F7"

def on_enter(e, widget, hover_color):
    if widget['state'] != tk.DISABLED:
        widget['background'] = hover_color

def on_leave(e, widget, default_color):
    if widget['state'] != tk.DISABLED:
        widget['background'] = default_color

def custom_button(parent, text, command, bg_color, hover_color, width=None):
    btn = tk.Button(parent, text=text, command=command, bg=bg_color, fg="white",
                    disabledforeground="#A0A0A0", activebackground=hover_color, activeforeground="white",
                    font=("Consolas", 10, "bold"), relief="flat", cursor="hand2", pady=5)
    if width:
        btn.config(width=width)
    btn.bind("<Enter>", lambda e: on_enter(e, btn, hover_color))
    btn.bind("<Leave>", lambda e: on_leave(e, btn, bg_color))
    return btn

# ==========================================
# 1. AUDIT LOGGING SETUP & DATABASE
# ==========================================
def setup_logger():
    log_dir = "app_logging"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    logging.basicConfig(
        filename=os.path.join(log_dir, "app.log"),
        level=logging.INFO,
        format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    return logging.getLogger("HardwareApp")

logger = setup_logger()
DB_NAME = "hardware_inventory_midterm.db"

def init_db():
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME, timeout=5)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            failed_attempts INTEGER DEFAULT 0,
            is_locked INTEGER DEFAULT 0
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_requests (
            req_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            status TEXT DEFAULT 'Pending'
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS hardware (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            status TEXT NOT NULL
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS borrow_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            item_name TEXT NOT NULL,
            username TEXT NOT NULL,
            borrowed_qty INTEGER NOT NULL,
            borrow_date TEXT NOT NULL,
            return_date TEXT,
            status TEXT DEFAULT 'Borrowed'
        )
        """)
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Database setup error: {e}")
    finally:
        if conn:
            conn.close()

# ==========================================
# 2. TABBED AUTHENTICATION PORTAL
# ==========================================
class AuthWindow:
    def __init__(self, root, on_success_callback):
        self.root = root
        self.on_success = on_success_callback
        self.root.title("Engineering Asset Tracker - Portal")
        self.root.geometry("450x520")
        self.root.configure(bg=BG_COLOR)
        self.root.resizable(False, False)
        
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tab_login = tk.Frame(self.notebook, bg=BG_COLOR)
        self.tab_register = tk.Frame(self.notebook, bg=BG_COLOR)
        self.tab_reset = tk.Frame(self.notebook, bg=BG_COLOR)
        
        self.notebook.add(self.tab_login, text="   LOGIN   ")
        self.notebook.add(self.tab_register, text="  REGISTER  ")
        self.notebook.add(self.tab_reset, text="  RESET PASS  ")
        
        self.build_login()
        self.build_register()
        self.build_reset()

    def build_login(self):
        tk.Label(self.tab_login, text="[ SYSTEM LOGIN ]", font=("Consolas", 14, "bold"), bg=BG_COLOR, fg=ACCENT_BLUE).pack(pady=(30, 10))
        frame_inputs = tk.Frame(self.tab_login, bg=BG_COLOR)
        frame_inputs.pack(pady=10)
        
        tk.Label(frame_inputs, text="Username:", font=("Consolas", 10), bg=BG_COLOR, fg=TEXT_COLOR).grid(row=0, column=0, sticky="w", padx=5, pady=10)
        self.entry_user_log = ttk.Entry(frame_inputs, width=25, font=("Consolas", 11), style="Normal.TEntry")
        self.entry_user_log.grid(row=0, column=1, padx=5, pady=10)
        
        tk.Label(frame_inputs, text="Password:", font=("Consolas", 10), bg=BG_COLOR, fg=TEXT_COLOR).grid(row=1, column=0, sticky="w", padx=5, pady=10)
        self.entry_pass_log = ttk.Entry(frame_inputs, show="*", width=25, font=("Consolas", 11), style="Normal.TEntry")
        self.entry_pass_log.grid(row=1, column=1, padx=5, pady=10)
        
        self.show_pass_var_log = tk.IntVar()
        chk_show = tk.Checkbutton(self.tab_login, text="Show Password", variable=self.show_pass_var_log, command=self.toggle_login_password,
                                  bg=BG_COLOR, fg=TEXT_COLOR, activebackground=BG_COLOR, activeforeground=TEXT_COLOR, selectcolor=PANEL_BG)
        chk_show.pack(anchor="w", padx=45, pady=(0, 10))
        
        btn_frame = tk.Frame(self.tab_login, bg=BG_COLOR)
        btn_frame.pack(pady=5)
        custom_button(btn_frame, ">> LOGIN <<", self.login, ACCENT_GREEN, "#2EA043", width=14).pack(side="left", padx=5)
        
        custom_button(btn_frame, "REGISTER", lambda: self.notebook.select(1), ACCENT_BLUE, "#79C0FF", width=12).pack(side="right", padx=5)
        custom_button(self.tab_login, "[ FORGOT PASSWORD? ]", lambda: self.notebook.select(2), ACCENT_YELLOW, "#D1A12A", width=28).pack(pady=15)

    def toggle_login_password(self):
        self.entry_pass_log.config(show="" if self.show_pass_var_log.get() else "*")

    def login(self):
        user = self.entry_user_log.get().strip()
        pw = self.entry_pass_log.get().strip()
        conn = None
        try:
            conn = sqlite3.connect(DB_NAME, timeout=5)
            cursor = conn.cursor()
            cursor.execute("SELECT id, password_hash, role, failed_attempts, is_locked FROM users WHERE username=?", (user,))
            row = cursor.fetchone()
            
            if not row:
                messagebox.showerror("Access Denied", "Invalid username or password.")
                return
                
            user_id, hashed_pw, role, failed_attempts, is_locked = row
            
            if is_locked == 1:
                prompt = messagebox.askyesno("Account Locked", "Account locked due to multiple failed attempts.\n\nWould you like to request a password reset?")
                if prompt:
                    self.notebook.select(2)
                    self.entry_user_res.delete(0, tk.END)
                    self.entry_user_res.insert(0, user)
                return

            if bcrypt.checkpw(pw.encode('utf-8'), hashed_pw.encode('utf-8')):
                cursor.execute("UPDATE users SET failed_attempts = 0 WHERE id=?", (user_id,))
                conn.commit()
                logger.info(f"User {user} ({role}) logged in successfully.")
                self.on_success(user, role)
            else:
                failed_attempts += 1
                if failed_attempts >= 3:
                    cursor.execute("UPDATE users SET failed_attempts = ?, is_locked = 1 WHERE id=?", (failed_attempts, user_id))
                    conn.commit()
                    logger.warning(f"User {user} permanently locked out.")
                    prompt = messagebox.askyesno("Account Locked", "3 consecutive failed attempts.\nAccount has been PERMANENTLY LOCKED.\n\nWould you like to reset your password?")
                    if prompt:
                        self.notebook.select(2)
                        self.entry_user_res.delete(0, tk.END)
                        self.entry_user_res.insert(0, user) 
                else:
                    cursor.execute("UPDATE users SET failed_attempts = ? WHERE id=?", (failed_attempts, user_id))
                    conn.commit()
                    messagebox.showerror("Access Denied", f"Invalid password. Attempt {failed_attempts}/3.")
        except sqlite3.Error as e:
            logger.error(f"Login error: {e}")
        finally:
            if conn: conn.close()

    def build_register(self):
        tk.Label(self.tab_register, text="[ NEW ACCOUNT ]", font=("Consolas", 13, "bold"), bg=BG_COLOR, fg=ACCENT_BLUE).pack(pady=(20, 10))
        frame_inputs = tk.Frame(self.tab_register, bg=BG_COLOR)
        frame_inputs.pack(pady=5)
        
        tk.Label(frame_inputs, text="Username:", font=("Consolas", 10), bg=BG_COLOR, fg=TEXT_COLOR).grid(row=0, column=0, sticky="w", padx=5, pady=10)
        self.entry_user_reg = ttk.Entry(frame_inputs, width=25, font=("Consolas", 11), style="Normal.TEntry")
        self.entry_user_reg.grid(row=0, column=1, padx=5, pady=10)
        
        tk.Label(frame_inputs, text="Email:", font=("Consolas", 10), bg=BG_COLOR, fg=TEXT_COLOR).grid(row=1, column=0, sticky="w", padx=5, pady=10)
        self.entry_email_reg = ttk.Entry(frame_inputs, width=25, font=("Consolas", 11), style="Normal.TEntry")
        self.entry_email_reg.grid(row=1, column=1, padx=5, pady=10)
        
        tk.Label(frame_inputs, text="User Role:", font=("Consolas", 10), bg=BG_COLOR, fg=TEXT_COLOR).grid(row=2, column=0, sticky="w", padx=5, pady=10)
        self.combo_role_reg = ttk.Combobox(frame_inputs, values=["User", "Admin"], state="readonly", width=23, font=("Consolas", 11))
        self.combo_role_reg.current(0)
        self.combo_role_reg.grid(row=2, column=1, padx=5, pady=10)
        
        tk.Label(frame_inputs, text="Password:", font=("Consolas", 10), bg=BG_COLOR, fg=TEXT_COLOR).grid(row=3, column=0, sticky="w", padx=5, pady=10)
        self.entry_pass_reg = ttk.Entry(frame_inputs, show="*", width=25, font=("Consolas", 11), style="Normal.TEntry")
        self.entry_pass_reg.grid(row=3, column=1, padx=5, pady=10)
        
        self.show_pass_var_reg = tk.IntVar()
        chk_show = tk.Checkbutton(self.tab_register, text="Show Password to Verify", variable=self.show_pass_var_reg, command=self.toggle_register_password,
                                  bg=BG_COLOR, fg=ACCENT_YELLOW, activebackground=BG_COLOR, activeforeground=TEXT_COLOR, selectcolor=PANEL_BG)
        chk_show.pack(anchor="w", padx=45, pady=(0, 10))
        
        custom_button(self.tab_register, ">> CREATE ACCOUNT <<", self.register, ACCENT_BLUE, "#79C0FF", width=24).pack(pady=10)

    def toggle_register_password(self):
        self.entry_pass_reg.config(show="" if self.show_pass_var_reg.get() else "*")

    def register(self):
        user, email, role, pw = self.entry_user_reg.get().strip(), self.entry_email_reg.get().strip(), self.combo_role_reg.get(), self.entry_pass_reg.get().strip()
        if not re.match("^[a-zA-Z0-9_]{3,20}$", user):
            messagebox.showwarning("Validation Error", "Username must be 3-20 chars.")
            return
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            messagebox.showwarning("Validation Error", "Invalid email format.")
            return
        if len(pw) < 8 or not re.search(r'[A-Z]', pw) or not re.search(r'\d', pw):
            messagebox.showwarning("Validation Error", "Password requires 8 chars, 1 uppercase, and 1 number.")
            return
        hashed_pw = bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt())
        conn = None
        try:
            conn = sqlite3.connect(DB_NAME, timeout=5)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)", (user, email, hashed_pw.decode('utf-8'), role))
            conn.commit()
            logger.info(f"Account created: {user} as {role}")
            messagebox.showinfo("Success", f"Registration successful as {role}! You may now login.")
            self.notebook.select(0) 
        except sqlite3.IntegrityError as e:
            if "email" in str(e).lower(): messagebox.showerror("Error", "Email already registered.")
            else: messagebox.showerror("Error", "Username already taken.")
        finally:
            if conn: conn.close()

    def build_reset(self):
        tk.Label(self.tab_reset, text="[ INITIATE RESET PROTOCOL ]", font=("Consolas", 13, "bold"), bg=BG_COLOR, fg=ACCENT_YELLOW).pack(pady=(40, 15))
        frame_inputs = tk.Frame(self.tab_reset, bg=BG_COLOR)
        frame_inputs.pack(pady=10)
        
        tk.Label(frame_inputs, text="Username:", font=("Consolas", 10), bg=BG_COLOR, fg=TEXT_COLOR).grid(row=0, column=0, sticky="w", padx=5, pady=10)
        self.entry_user_res = ttk.Entry(frame_inputs, width=25, font=("Consolas", 11), style="Normal.TEntry")
        self.entry_user_res.grid(row=0, column=1, padx=5, pady=10)
        
        tk.Label(frame_inputs, text="Registered Email:", font=("Consolas", 10), bg=BG_COLOR, fg=TEXT_COLOR).grid(row=1, column=0, sticky="w", padx=5, pady=10)
        self.entry_email_res = ttk.Entry(frame_inputs, width=25, font=("Consolas", 11), style="Normal.TEntry")
        self.entry_email_res.grid(row=1, column=1, padx=5, pady=10)
        
        custom_button(self.tab_reset, "SUBMIT TICKET", self.submit_request, ACCENT_YELLOW, "#D1A12A", width=20).pack(pady=20)

    def submit_request(self):
        user, email = self.entry_user_res.get().strip(), self.entry_email_res.get().strip()
        conn = None
        try:
            conn = sqlite3.connect(DB_NAME, timeout=5)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username=? AND email=?", (user, email))
            if not cursor.fetchone():
                messagebox.showerror("Error", "Username and Email combination not found.")
                return
            cursor.execute("SELECT req_id FROM password_requests WHERE username=? AND status='Pending'", (user,))
            if cursor.fetchone():
                messagebox.showinfo("Status", "You already have a pending reset request.")
                return
            cursor.execute("INSERT INTO password_requests (username, email) VALUES (?, ?)", (user, email))
            conn.commit()
            logger.info(f"Password reset requested for {user}")
            messagebox.showinfo("Request Sent", "Request submitted successfully! An Admin will review it.")
            self.notebook.select(0) 
        finally:
            if conn: conn.close()

# ==========================================
# 3. PROFILE / SECURITY VIEW (INLINE)
# ==========================================
class ProfileView:
    def __init__(self, root, username, role, on_back_callback):
        self.root = root
        self.username = username
        self.role = role
        self.on_back = on_back_callback
        
        self.root.title(f"Engineering Asset Tracking System - Profile: {self.username}")
        self.root.geometry("1000x750")
        self.root.configure(bg=BG_COLOR)
        
        self.build_ui()

    def build_ui(self):
        main_frame = tk.Frame(self.root, bg=BG_COLOR)
        main_frame.place(relx=0.5, rely=0.45, anchor="center")
        
        tk.Label(main_frame, text="[ PROFILE & SECURITY ]", font=("Consolas", 18, "bold"), bg=BG_COLOR, fg=ACCENT_PURPLE).pack(pady=(0, 20))
        
        info_frame = tk.Frame(main_frame, bg=PANEL_BG, padx=25, pady=20, relief="ridge", bd=1)
        info_frame.pack(fill="x", pady=10)
        
        tk.Label(info_frame, text=f"Account Name : {self.username}", font=("Consolas", 12), bg=PANEL_BG, fg=TEXT_COLOR).pack(anchor="w")
        tk.Label(info_frame, text=f"Assigned Role: {self.role}", font=("Consolas", 12), bg=PANEL_BG, fg=TEXT_COLOR).pack(anchor="w", pady=(10, 0))
        
        tk.Label(main_frame, text="-- Change Password --", font=("Consolas", 12, "bold"), bg=BG_COLOR, fg=ACCENT_BLUE).pack(pady=(30, 10))
        
        form_frame = tk.Frame(main_frame, bg=BG_COLOR)
        form_frame.pack()
        
        tk.Label(form_frame, text="Current Pass:", font=("Consolas", 11), bg=BG_COLOR, fg=TEXT_COLOR).grid(row=0, column=0, sticky="e", padx=10, pady=10)
        self.entry_curr = ttk.Entry(form_frame, show="*", width=30, font=("Consolas", 11), style="Normal.TEntry")
        self.entry_curr.grid(row=0, column=1, padx=10, pady=10)
        
        tk.Label(form_frame, text="New Password:", font=("Consolas", 11), bg=BG_COLOR, fg=TEXT_COLOR).grid(row=1, column=0, sticky="e", padx=10, pady=10)
        self.entry_new = ttk.Entry(form_frame, show="*", width=30, font=("Consolas", 11), style="Normal.TEntry")
        self.entry_new.grid(row=1, column=1, padx=10, pady=10)
        
        tk.Label(form_frame, text="Confirm Pass:", font=("Consolas", 11), bg=BG_COLOR, fg=TEXT_COLOR).grid(row=2, column=0, sticky="e", padx=10, pady=10)
        self.entry_conf = ttk.Entry(form_frame, show="*", width=30, font=("Consolas", 11), style="Normal.TEntry")
        self.entry_conf.grid(row=2, column=1, padx=10, pady=10)
        
        btn_frame = tk.Frame(main_frame, bg=BG_COLOR)
        btn_frame.pack(pady=30)
        
        custom_button(btn_frame, "<< BACK TO INVENTORY", self.on_back, "#555555", "#777777", width=22).pack(side="left", padx=10)
        custom_button(btn_frame, "UPDATE SECURITY", self.change_password, ACCENT_GREEN, "#2EA043", width=20).pack(side="left", padx=10)

    def change_password(self):
        curr_p, new_p, conf_p = self.entry_curr.get().strip(), self.entry_new.get().strip(), self.entry_conf.get().strip()
        if new_p != conf_p:
            messagebox.showerror("Error", "New passwords do not match.")
            return
        if len(new_p) < 8 or not re.search(r'[A-Z]', new_p) or not re.search(r'\d', new_p):
            messagebox.showwarning("Validation Error", "Password must have at least 8 chars, 1 uppercase, 1 number.")
            return
        conn = None
        try:
            conn = sqlite3.connect(DB_NAME, timeout=5)
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash FROM users WHERE username=?", (self.username,))
            row = cursor.fetchone()
            if row and bcrypt.checkpw(curr_p.encode('utf-8'), row[0].encode('utf-8')):
                hashed_new = bcrypt.hashpw(new_p.encode('utf-8'), bcrypt.gensalt())
                cursor.execute("UPDATE users SET password_hash=? WHERE username=?", (hashed_new.decode('utf-8'), self.username))
                conn.commit()
                messagebox.showinfo("Success", "Password updated successfully!")
                self.on_back()
            else:
                messagebox.showerror("Auth Error", "Incorrect Current Password.")
        finally:
            if conn: conn.close()

# ==========================================
# 4. ADMIN APPROVALS & UTILITIES
# ==========================================
class AdminApprovalWindow:
    def __init__(self, parent):
        self.top = tk.Toplevel(parent)
        self.top.title("Admin Panel: Unlock Requests")
        self.top.geometry("550x450")
        self.top.configure(bg=BG_COLOR)
        tk.Label(self.top, text="[ PENDING RESET REQUESTS ]", font=("Consolas", 12, "bold"), bg=BG_COLOR, fg=ACCENT_YELLOW).pack(pady=15)
        self.tree = ttk.Treeview(self.top, columns=("ID", "Username", "Email", "Status"), show="headings", height=10)
        for col in ("ID", "Username", "Email", "Status"):
            self.tree.heading(col, text=col.upper())
        self.tree.column("ID", width=60, anchor="center")
        self.tree.column("Username", width=120)
        self.tree.column("Email", width=180)
        self.tree.column("Status", width=100, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=15, pady=5)
        btn_frame = tk.Frame(self.top, bg=BG_COLOR)
        btn_frame.pack(pady=15)
        custom_button(btn_frame, "APPROVE UNLOCK", self.approve_req, ACCENT_GREEN, "#2EA043").pack(side="left", padx=10)
        custom_button(btn_frame, "REJECT", self.reject_req, ACCENT_RED, "#F85149").pack(side="left", padx=10)
        self.load_requests()

    def load_requests(self):
        for row in self.tree.get_children(): self.tree.delete(row)
        conn = None
        try:
            conn = sqlite3.connect(DB_NAME, timeout=5)
            cursor = conn.cursor()
            cursor.execute("SELECT req_id, username, email, status FROM password_requests WHERE status='Pending'")
            for row in cursor.fetchall(): self.tree.insert("", tk.END, values=row)
        finally:
            if conn: conn.close()

    def get_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selection Error", "Please select a request.", parent=self.top)
            return None
        return self.tree.item(selected[0], "values")

    def approve_req(self):
        data = self.get_selected()
        if not data: return
        conn = None
        try:
            conn = sqlite3.connect(DB_NAME, timeout=5)
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET is_locked = 0, failed_attempts = 0 WHERE username = ?", (data[1],))
            cursor.execute("DELETE FROM password_requests WHERE req_id = ?", (data[0],))
            conn.commit()
            messagebox.showinfo("Approved", f"Account '{data[1]}' unlocked.", parent=self.top)
            self.load_requests()
        finally:
            if conn: conn.close()

    def reject_req(self):
        data = self.get_selected()
        if not data: return
        conn = None
        try:
            conn = sqlite3.connect(DB_NAME, timeout=5)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM password_requests WHERE req_id = ?", (data[0],))
            conn.commit()
            messagebox.showinfo("Rejected", f"Request for '{data[1]}' rejected.", parent=self.top)
            self.load_requests()
        finally:
            if conn: conn.close()

class MultiBorrowWindow:
    def __init__(self, parent, user, checked_items, confirm_callback):
        self.top = tk.Toplevel(parent)
        self.top.title("Confirm Borrow Quantities")
        self.top.geometry("450x400")
        self.top.configure(bg=PANEL_BG)
        self.confirm_callback = confirm_callback
        self.user = user
        self.items = checked_items
        self.qty_entries = {}
        
        tk.Label(self.top, text="[ SPECIFY QUANTITY PER ITEM ]", bg=PANEL_BG, fg=ACCENT_YELLOW, font=("Consolas", 12, "bold")).pack(pady=15)
        
        frame_list = tk.Frame(self.top, bg=PANEL_BG)
        frame_list.pack(fill="both", expand=True, padx=20)
        
        tk.Label(frame_list, text="Item Name", bg=PANEL_BG, fg=TEXT_COLOR, font=("Consolas", 10, "bold")).grid(row=0, column=0, sticky="w", padx=5)
        tk.Label(frame_list, text="Avail", bg=PANEL_BG, fg=TEXT_COLOR, font=("Consolas", 10, "bold")).grid(row=0, column=1, padx=5)
        tk.Label(frame_list, text="Borrow Qty", bg=PANEL_BG, fg=TEXT_COLOR, font=("Consolas", 10, "bold")).grid(row=0, column=2, padx=5)
        
        for i, item in enumerate(self.items):
            item_id, name, avail_qty = item[1], item[2], item[4] 
            
            tk.Label(frame_list, text=name[:20], bg=PANEL_BG, fg=ACCENT_BLUE).grid(row=i+1, column=0, sticky="w", padx=5, pady=5)
            tk.Label(frame_list, text=str(avail_qty), bg=PANEL_BG, fg=TEXT_COLOR).grid(row=i+1, column=1, padx=5, pady=5)
            
            e_var = tk.StringVar(value="1")
            e_box = ttk.Entry(frame_list, textvariable=e_var, width=8, justify="center")
            e_box.grid(row=i+1, column=2, padx=5, pady=5)
            
            self.qty_entries[item_id] = {"name": name, "avail": int(avail_qty), "var": e_var}
            
        custom_button(self.top, "CONFIRM BORROW", self.process_borrow, ACCENT_GREEN, "#2EA043").pack(pady=20)

    def process_borrow(self):
        final_list = []
        for item_id, data in self.qty_entries.items():
            try:
                qty = int(data["var"].get())
                if qty <= 0 or qty > data["avail"]:
                    messagebox.showerror("Error", f"Invalid quantity for {data['name']}. Must be 1 to {data['avail']}.", parent=self.top)
                    return
                final_list.append((item_id, data["name"], qty, data["avail"]))
            except ValueError:
                messagebox.showerror("Error", f"Please enter a valid number for {data['name']}.", parent=self.top)
                return
        
        self.confirm_callback(final_list)
        self.top.destroy()

# ==========================================
# 5. MAIN APPLICATION INTERFACE
# ==========================================
class InventoryWindow:
    def __init__(self, root, current_user, user_role, on_logout_callback, on_profile_callback):
        self.root = root
        self.current_user = current_user
        self.user_role = user_role 
        self.on_logout = on_logout_callback
        self.on_profile = on_profile_callback
        self.editing_id = None 
        
        self.root.title(f"Engineering Asset Tracking System - {current_user} [{user_role}]")
        self.root.geometry("1000x750")
        self.root.configure(bg=BG_COLOR)
        
        self.build_ui()
        self.load_inventory()
        self.load_borrow_logs()

    def build_ui(self):
        header_frame = tk.Frame(self.root, bg=BG_COLOR)
        header_frame.pack(fill="x", padx=15, pady=10)
        self.lbl_valuation = tk.Label(header_frame, text="TOTAL INVENTORY VALUE: ₱0.00", font=("Consolas", 12, "bold"), fg=ACCENT_GREEN, bg=BG_COLOR)
        self.lbl_valuation.pack(side="left")
        btn_logout = custom_button(header_frame, "LOGOUT", self.logout, ACCENT_RED, "#F85149")
        btn_logout.pack(side="right")
        btn_profile = custom_button(header_frame, "MY PROFILE", self.open_profile, ACCENT_PURPLE, "#8952DB")
        btn_profile.pack(side="right", padx=10)

        if self.user_role == "Admin":
            btn_admin = custom_button(header_frame, "ADMIN APPROVALS", self.open_admin_panel, ACCENT_YELLOW, "#D1A12A")
            btn_admin.pack(side="right", padx=0)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=5)
        
        self.tab_catalog = tk.Frame(self.notebook, bg=BG_COLOR)
        self.tab_logbook = tk.Frame(self.notebook, bg=BG_COLOR)
        
        self.notebook.add(self.tab_catalog, text="[ ASSET CATALOG ]")
        self.notebook.add(self.tab_logbook, text="[ ACTIVE LOGBOOK ]")

        self.build_catalog_tab()
        self.build_logbook_tab()

    def build_catalog_tab(self):
        if self.user_role == "Admin":
            self.form_label = tk.StringVar(value=" [+] REGISTER / UPDATE ASSET ")
            input_frame = tk.LabelFrame(self.tab_catalog, labelwidget=tk.Label(self.tab_catalog, textvariable=self.form_label, bg=BG_COLOR, fg=ACCENT_BLUE, font=("Consolas", 11, "bold")), bg=BG_COLOR, bd=1)
            input_frame.pack(fill="x", padx=15, pady=5)
            
            tk.Label(input_frame, text="Item Name:", bg=BG_COLOR, fg=TEXT_COLOR, font=("Consolas", 10)).grid(row=0, column=0, sticky="e", padx=5, pady=10)
            self.item_name_var = tk.StringVar()
            self.e_name = ttk.Entry(input_frame, width=22, font=("Consolas", 10), textvariable=self.item_name_var, style="Normal.TEntry")
            self.e_name.grid(row=0, column=1, padx=5, pady=10)
            
            tk.Label(input_frame, text="Category:", bg=BG_COLOR, fg=TEXT_COLOR, font=("Consolas", 10)).grid(row=0, column=2, sticky="e", padx=5, pady=10)
            self.e_category = ttk.Entry(input_frame, width=22, font=("Consolas", 10), style="Normal.TEntry")
            self.e_category.grid(row=0, column=3, padx=5, pady=10)
            
            tk.Label(input_frame, text="Avail. Qty:", bg=BG_COLOR, fg=TEXT_COLOR, font=("Consolas", 10)).grid(row=1, column=0, sticky="e", padx=5, pady=10)
            self.e_qty = ttk.Entry(input_frame, width=22, font=("Consolas", 10), style="Normal.TEntry")
            self.e_qty.grid(row=1, column=1, padx=5, pady=10)
            
            tk.Label(input_frame, text="Unit Price (₱):", bg=BG_COLOR, fg=TEXT_COLOR, font=("Consolas", 10)).grid(row=1, column=2, sticky="e", padx=5, pady=10)
            self.e_price = ttk.Entry(input_frame, width=22, font=("Consolas", 10), style="Normal.TEntry")
            self.e_price.grid(row=1, column=3, padx=5, pady=10)
            
            self.btn_save = custom_button(input_frame, ">> SAVE ITEM <<", self.save_item, ACCENT_GREEN, "#2EA043")
            self.btn_save.grid(row=1, column=4, padx=15, pady=10)
            self.btn_cancel_edit = custom_button(input_frame, "CANCEL", self.cancel_edit, "#555555", "#777777")

        search_frame = tk.Frame(self.tab_catalog, bg=BG_COLOR)
        search_frame.pack(fill="x", padx=15, pady=(10, 0))
        tk.Label(search_frame, text="Search Asset:", bg=BG_COLOR, fg=TEXT_COLOR, font=("Consolas", 10)).pack(side="left")
        self.entry_search = ttk.Entry(search_frame, font=("Consolas", 10), width=25, style="Normal.TEntry")
        self.entry_search.pack(side="left", padx=5)
        custom_button(search_frame, "SEARCH", self.search_data, ACCENT_BLUE, "#79C0FF").pack(side="left", padx=5)
        custom_button(search_frame, "RESET", self.load_inventory, "#555555", "#777777").pack(side="left", padx=5)

        grid_frame = tk.Frame(self.tab_catalog, bg=BG_COLOR)
        grid_frame.pack(fill="both", expand=True, padx=15, pady=5)
        
        scroll = ttk.Scrollbar(grid_frame)
        scroll.pack(side="right", fill="y")
        
        self.tree = ttk.Treeview(grid_frame, columns=("Select", "ID", "Name", "Category", "Qty", "Price", "Status"), show="headings", yscrollcommand=scroll.set, selectmode="none")
        self.tree.heading("Select", text="☑ / ☐")
        for col in ("ID", "Name", "Category", "Qty", "Price", "Status"):
            self.tree.heading(col, text=col.upper())
            
        self.tree.column("Select", width=60, anchor="center")
        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Category", width=120, anchor="center")
        self.tree.column("Qty", width=80, anchor="center")
        self.tree.column("Price", width=100, anchor="center")
        self.tree.column("Status", width=120, anchor="center")
        self.tree.column("Name", width=200)
        self.tree.pack(fill="both", expand=True)
        
        self.tree.bind("<ButtonPress-1>", self.toggle_catalog_check)
        
        # UPDATED DYNAMIC COLOR TAGS FOR NEW STOCK LOGIC
        self.tree.tag_configure("High Stock", background="#004A00", foreground="white") # Green
        self.tree.tag_configure("Mid Stock", background="#7A6300", foreground="white")  # Yellow
        self.tree.tag_configure("Low Stock", background=ACCENT_RED, foreground="white") # Red
        self.tree.tag_configure("Out of Stock", background="#4A0000", foreground="#8B949E") # Dark Red/Gray

        action_frame = tk.Frame(self.tab_catalog, bg=BG_COLOR)
        action_frame.pack(fill="x", padx=15, pady=10)
        
        custom_button(action_frame, "BORROW SELECTED", self.process_multi_borrow, ACCENT_YELLOW, "#D1A12A").pack(side="left", padx=5)
        
        if self.user_role == "Admin":
            custom_button(action_frame, "MODIFY ITEM", self.prepare_modify, ACCENT_BLUE, "#79C0FF").pack(side="left", padx=10)
            custom_button(action_frame, "DELETE ITEM", self.delete_item, ACCENT_RED, "#F85149").pack(side="left", padx=0)
            custom_button(action_frame, "EXPORT INVENTORY", self.export_csv, ACCENT_GREEN, "#2EA043").pack(side="right", padx=0)

    def build_logbook_tab(self):
        lbl_info = tk.Label(self.tab_logbook, text="Currently Borrowed Laboratory Assets (Preventing Resource Conflicts)", font=("Consolas", 11, "italic"), bg=BG_COLOR, fg="#8B949E")
        lbl_info.pack(pady=10, anchor="w", padx=15)
        log_frame = tk.Frame(self.tab_logbook, bg=BG_COLOR)
        log_frame.pack(fill="both", expand=True, padx=15, pady=5)
        scroll_log = ttk.Scrollbar(log_frame)
        scroll_log.pack(side="right", fill="y")
        
        self.log_tree = ttk.Treeview(log_frame, columns=("Select", "LogID", "Asset Name", "Borrower", "Qty", "Borrow Date", "Return Date", "Status"), show="headings", yscrollcommand=scroll_log.set, selectmode="extended")
        self.log_tree.heading("Select", text="☑ / ☐")
        for col in ("LogID", "Asset Name", "Borrower", "Qty", "Borrow Date", "Return Date", "Status"):
            self.log_tree.heading(col, text=col.upper())
            
        self.log_tree.column("Select", width=60, anchor="center")
        self.log_tree.column("LogID", width=60, anchor="center")
        self.log_tree.column("Borrower", width=100, anchor="center")
        self.log_tree.column("Qty", width=60, anchor="center")
        self.log_tree.column("Borrow Date", width=140, anchor="center")
        self.log_tree.column("Return Date", width=140, anchor="center")
        self.log_tree.column("Status", width=100, anchor="center")
        self.log_tree.column("Asset Name", width=180)
        self.log_tree.pack(fill="both", expand=True)
        
        self.log_tree.bind("<ButtonPress-1>", self.toggle_logbook_check)
        
        self.log_tree.tag_configure("Borrowed", background="#3B3B00", foreground="white") 
        self.log_tree.tag_configure("Returned", background="#003B00", foreground="#8B949E") 
        log_action_frame = tk.Frame(self.tab_logbook, bg=BG_COLOR)
        log_action_frame.pack(fill="x", padx=15, pady=10)
        
        custom_button(log_action_frame, "RETURN SELECTED", self.return_item, ACCENT_GREEN, "#2EA043").pack(side="left", padx=5)
        
        if self.user_role == "Admin":
            custom_button(log_action_frame, "EXPORT LOGBOOK", self.export_logbook_csv, ACCENT_GREEN, "#2EA043").pack(side="right", padx=0)

    def open_admin_panel(self): AdminApprovalWindow(self.root)
    def open_profile(self): self.on_profile()

    def toggle_catalog_check(self, event):
        item_id = self.tree.identify_row(event.y)
        if item_id:
            values = list(self.tree.item(item_id, "values"))
            values[0] = "☑" if values[0] == "☐" else "☐"
            self.tree.item(item_id, values=values)
            if values[0] == "☑":
                self.tree.selection_add(item_id)
            else:
                self.tree.selection_remove(item_id)
        return "break" 

    def toggle_logbook_check(self, event):
        item_id = self.log_tree.identify_row(event.y)
        if item_id:
            values = list(self.log_tree.item(item_id, "values"))
            if values[7] == "Returned":
                messagebox.showinfo("Info", "This item has already been returned.")
                return "break"
            values[0] = "☑" if values[0] == "☐" else "☐"
            self.log_tree.item(item_id, values=values)
            if values[0] == "☑":
                self.log_tree.selection_add(item_id)
            else:
                self.log_tree.selection_remove(item_id)
        return "break"

    def search_data(self):
        query = self.entry_search.get().strip()
        if not query: return self.load_inventory()
        for row in self.tree.get_children(): self.tree.delete(row)
        conn = None
        try:
            conn = sqlite3.connect(DB_NAME, timeout=5)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM hardware WHERE item_name LIKE ?", ('%' + query + '%',))
            for row in cursor.fetchall():
                # Dynamically fetch actual updated status on search
                actual_status = self.compute_status(row[3])
                formatted_row = ("☐", row[0], row[1], row[2], row[3], f"₱{row[4]:.2f}", actual_status)
                self.tree.insert("", tk.END, values=formatted_row, tags=(actual_status,))
        finally:
            if conn: conn.close()

    # --- UPDATED STOCK LOGIC ---
    def compute_status(self, qty):
        if qty == 0: return 'Out of Stock'
        elif 1 <= qty <= 5: return 'Low Stock'
        elif 6 <= qty <= 10: return 'Mid Stock'
        else: return 'High Stock'

    def update_valuation(self):
        conn = None
        try:
            conn = sqlite3.connect(DB_NAME, timeout=5)
            cursor = conn.cursor()
            cursor.execute("SELECT SUM(quantity * unit_price) FROM hardware")
            total = cursor.fetchone()[0]
            self.lbl_valuation.config(text=f"TOTAL INVENTORY VALUE: ₱{total if total else 0.0:,.2f}")
        finally:
            if conn: conn.close()

    def load_inventory(self):
        self.entry_search.delete(0, tk.END)
        for row in self.tree.get_children(): self.tree.delete(row)
        conn = None
        try:
            conn = sqlite3.connect(DB_NAME, timeout=5)
            cursor = conn.cursor()
            
            # This automatically updates old data statuses based on the new logic behind the scenes
            cursor.execute("SELECT * FROM hardware")
            for row in cursor.fetchall():
                item_id, qty, db_status = row[0], row[3], row[5]
                actual_status = self.compute_status(qty)
                if db_status != actual_status:
                    cursor.execute("UPDATE hardware SET status=? WHERE item_id=?", (actual_status, item_id))
                    db_status = actual_status
            conn.commit()

            cursor.execute("SELECT * FROM hardware")
            for row in cursor.fetchall():
                formatted_row = ("☐", row[0], row[1], row[2], row[3], f"₱{row[4]:.2f}", row[5])
                self.tree.insert("", tk.END, values=formatted_row, tags=(row[5],))
        finally:
            if conn: conn.close()
        self.update_valuation()

    def load_borrow_logs(self):
        for row in self.log_tree.get_children(): self.log_tree.delete(row)
        conn = None
        try:
            conn = sqlite3.connect(DB_NAME, timeout=5)
            cursor = conn.cursor()
            if self.user_role == "Admin":
                cursor.execute("SELECT * FROM borrow_logs ORDER BY status ASC, log_id DESC")
            else:
                cursor.execute("SELECT * FROM borrow_logs WHERE username=? ORDER BY status ASC, log_id DESC", (self.current_user,))
            for row in cursor.fetchall():
                fmt_row = ("☐", row[0], row[2], row[3], row[4], row[5], row[6] if row[6] else "---", row[7])
                self.log_tree.insert("", tk.END, values=fmt_row, tags=(row[7],))
        finally:
            if conn: conn.close()

    def process_multi_borrow(self):
        checked_items = []
        for row_id in self.tree.get_children():
            values = self.tree.item(row_id, "values")
            if values[0] == "☑":
                checked_items.append(values)
                
        if not checked_items:
            messagebox.showwarning("Warning", "Please select at least one item from the catalog to borrow.")
            return
            
        q1 = messagebox.askyesno("Confirmation", "Do you wish to borrow the selected items?")
        if not q1: return
        
        q2 = messagebox.askyesno("Final Check", "Are you sure and don't want any changes?")
        if not q2: return
        
        MultiBorrowWindow(self.root, self.current_user, checked_items, self.execute_multi_borrow)

    def execute_multi_borrow(self, final_checkout_list):
        borrow_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn = None
        try:
            conn = sqlite3.connect(DB_NAME, timeout=5)
            cursor = conn.cursor()
            
            for item_id, item_name, borrow_qty, current_qty in final_checkout_list:
                new_qty = current_qty - borrow_qty
                new_status = self.compute_status(new_qty)
                cursor.execute("UPDATE hardware SET quantity=?, status=? WHERE item_id=?", (new_qty, new_status, item_id))
                cursor.execute("INSERT INTO borrow_logs (item_id, item_name, username, borrowed_qty, borrow_date) VALUES (?, ?, ?, ?, ?)",
                               (item_id, item_name, self.current_user, borrow_qty, borrow_date))
                logger.info(f"User {self.current_user} borrowed {borrow_qty}x {item_name}")
                
            conn.commit()
            messagebox.showinfo("Success", "All selected items have been successfully borrowed and logged.")
            messagebox.showwarning("Important Notice", "If any of the item you borrowed got broken, you must pay for the value of it. Thank you.")
            self.load_inventory()
            self.load_borrow_logs()
        except sqlite3.Error as e:
            logger.error(f"Multi-borrow error: {e}")
            messagebox.showerror("Error", "A database error occurred during borrowing.")
        finally:
            if conn: conn.close()

    def return_item(self):
        checked_items = []
        for row_id in self.log_tree.get_children():
            values = self.log_tree.item(row_id, "values")
            if values[0] == "☑":
                checked_items.append(values)
                
        if not checked_items:
            messagebox.showwarning("Warning", "Please select at least one record from the logbook to return.")
            return

        if messagebox.askyesno("Confirm Return", f"Are you sure you want to return the {len(checked_items)} selected item(s)?"):
            return_date = datetime.now().strftime("%Y-%m-%d %H:%M")
            conn = None
            try:
                conn = sqlite3.connect(DB_NAME, timeout=5)
                cursor = conn.cursor()
                
                for log_data in checked_items:
                    log_id = log_data[1]
                    item_name = log_data[2]
                    borrowed_qty = int(log_data[4])
                    
                    cursor.execute("UPDATE borrow_logs SET status='Returned', return_date=? WHERE log_id=?", (return_date, log_id))
                    cursor.execute("SELECT item_id FROM borrow_logs WHERE log_id=?", (log_id,))
                    item_id = cursor.fetchone()[0]
                    cursor.execute("SELECT quantity FROM hardware WHERE item_id=?", (item_id,))
                    current_qty = cursor.fetchone()[0]
                    
                    new_qty = current_qty + borrowed_qty
                    new_status = self.compute_status(new_qty)
                    cursor.execute("UPDATE hardware SET quantity=?, status=? WHERE item_id=?", (new_qty, new_status, item_id))
                    
                    logger.info(f"User {self.current_user} returned {borrowed_qty}x {item_name}")
                    
                conn.commit()
                messagebox.showinfo("Success", "Selected items have been returned to the lab.")
                messagebox.showinfo("Notice", "Thank you for borrowing it and keeping it safe!")
                
                self.load_inventory()
                self.load_borrow_logs()
            finally:
                if conn: conn.close()

    def prepare_modify(self):
        checked_items = [self.tree.item(r, "values") for r in self.tree.get_children() if self.tree.item(r, "values")[0] == "☑"]
        
        if len(checked_items) != 1:
            messagebox.showwarning("Warning", "Please select exactly ONE item to modify.")
            return
            
        item_data = checked_items[0]
        self.editing_id = item_data[1] 
        self.e_name.delete(0, tk.END); self.e_name.insert(0, item_data[2])
        self.e_category.delete(0, tk.END); self.e_category.insert(0, item_data[3])
        self.e_qty.delete(0, tk.END); self.e_qty.insert(0, item_data[4])
        self.e_price.delete(0, tk.END); self.e_price.insert(0, item_data[5].replace("₱", "").replace(",", ""))
        self.form_label.set(" [!] MODIFYING RECORD ID: " + self.editing_id + " ")
        self.btn_save.config(text=">> UPDATE ITEM <<", bg=ACCENT_BLUE)
        self.btn_cancel_edit.grid(row=1, column=5, padx=5, pady=10)

    def cancel_edit(self):
        self.editing_id = None
        self.form_label.set(" [+] REGISTER / UPDATE ASSET ")
        self.btn_save.config(text=">> SAVE ITEM <<", bg=ACCENT_GREEN)
        self.btn_cancel_edit.grid_remove()
        self.e_name.delete(0, tk.END); self.e_category.delete(0, tk.END)
        self.e_qty.delete(0, tk.END); self.e_price.delete(0, tk.END)

    def save_item(self):
        name, cat, qty_str, price_str = self.e_name.get().strip(), self.e_category.get().strip(), self.e_qty.get().strip(), self.e_price.get().strip()
        if not name or not cat or not qty_str or not price_str:
            messagebox.showwarning("Input Error", "All fields are required.")
            return
        try:
            qty, price = int(qty_str), float(price_str)
        except ValueError:
            messagebox.showerror("Format Error", "Quantity=Int, Price=Number.")
            return
        status = self.compute_status(qty)
        conn = None
        try:
            conn = sqlite3.connect(DB_NAME, timeout=5)
            cursor = conn.cursor()
            if self.editing_id: 
                cursor.execute("UPDATE hardware SET item_name=?, category=?, quantity=?, unit_price=?, status=? WHERE item_id=?",
                               (name, cat, qty, price, status, self.editing_id))
                self.cancel_edit()
            else:
                cursor.execute("SELECT item_name FROM hardware WHERE LOWER(item_name) = LOWER(?)", (name,))
                if cursor.fetchone():
                    messagebox.showerror("Duplicate", "Item already exists!")
                    return
                cursor.execute("INSERT INTO hardware (item_name, category, quantity, unit_price, status) VALUES (?, ?, ?, ?, ?)",
                               (name, cat, qty, price, status))
                self.e_name.delete(0, tk.END); self.e_category.delete(0, tk.END)
                self.e_qty.delete(0, tk.END); self.e_price.delete(0, tk.END)
            conn.commit()
            self.load_inventory()
        finally:
            if conn: conn.close()

    def delete_item(self):
        checked_items = [self.tree.item(r, "values") for r in self.tree.get_children() if self.tree.item(r, "values")[0] == "☑"]
        if not checked_items:
            messagebox.showwarning("Warning", "Select at least one item to delete.")
            return
            
        if messagebox.askyesno("Confirm Delete", f"Delete {len(checked_items)} selected item(s)?"):
            conn = sqlite3.connect(DB_NAME, timeout=5)
            for item in checked_items:
                conn.execute("DELETE FROM hardware WHERE item_id=?", (item[1],))
            conn.commit(); conn.close()
            self.load_inventory()

    def export_csv(self):
        conn = sqlite3.connect(DB_NAME, timeout=5)
        rows = conn.execute("SELECT * FROM hardware").fetchall()
        conn.close()
        filename = "engineering_assets_midterm.csv"
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Name", "Category", "Quantity", "Unit Price", "Status"])
            writer.writerows(rows)
        messagebox.showinfo("Exported", f"Data saved to {filename}")

    def export_logbook_csv(self):
        conn = sqlite3.connect(DB_NAME, timeout=5)
        rows = conn.execute("SELECT * FROM borrow_logs").fetchall()
        conn.close()
        filename = "engineering_logbook_midterm.csv"
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Log ID", "Item ID", "Asset Name", "Borrower Username", "Borrowed Quantity", "Borrow Date", "Return Date", "Status"])
            writer.writerows(rows)
        messagebox.showinfo("Exported", f"Logbook data saved to {filename}")

    def logout(self):
        self.on_logout()

# ==========================================
# 6. APP ROUTING & INLINE PROFILE VIEW
# ==========================================
class AppController:
    def __init__(self):
        init_db()
        self.root = tk.Tk()
        self.setup_styles()
        self.show_auth()
        self.root.mainloop()
        
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Normal.TEntry", fieldbackground=PANEL_BG, foreground=TEXT_COLOR, insertcolor=TEXT_COLOR, bordercolor=BG_COLOR)
        style.configure("TCombobox", fieldbackground=PANEL_BG, background=PANEL_BG, foreground="white")
        style.map("TCombobox", fieldbackground=[("readonly", PANEL_BG)], foreground=[("readonly", "white")], selectbackground=[("readonly", ACCENT_BLUE)])
        self.root.option_add("*TCombobox*Listbox*Background", PANEL_BG)
        self.root.option_add("*TCombobox*Listbox*Foreground", "white")

        style.configure("Treeview", background=PANEL_BG, foreground=TEXT_COLOR, rowheight=35, fieldbackground=PANEL_BG, bordercolor=BG_COLOR, font=("Consolas", 10))
        style.configure("Treeview.Heading", font=("Consolas", 10, "bold"), background="#21262D", foreground=ACCENT_BLUE)
        
        style.map('Treeview', background=[('selected', '#1F6FEB')], foreground=[('selected', 'white')])

        style.configure("TNotebook", background=BG_COLOR, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL_BG, foreground=TEXT_COLOR, padding=[20, 8], font=("Consolas", 11, "bold"), borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", ACCENT_BLUE)], foreground=[("selected", "white")])

    def clear_window(self):
        for widget in self.root.winfo_children(): widget.destroy()

    def show_auth(self):
        self.clear_window()
        self.root.geometry("450x520")
        AuthWindow(self.root, self.show_inventory)

    def show_inventory(self, username, role):
        self.clear_window()
        self.root.geometry("1000x750")
        InventoryWindow(self.root, username, role, self.show_auth, lambda: self.show_profile(username, role))

    def show_profile(self, username, role):
        self.clear_window()
        self.root.geometry("1000x750") # Profile matches Inventory size seamlessly
        ProfileView(self.root, username, role, lambda: self.show_inventory(username, role))

# ==========================================
# 7. INLINE PROFILE / SECURITY COMPONENT
# ==========================================
class ProfileView:
    def __init__(self, root, username, role, on_back_callback):
        self.root = root
        self.username = username
        self.role = role
        self.on_back = on_back_callback
        
        self.root.title(f"Engineering Asset Tracking System - Profile: {self.username}")
        self.root.configure(bg=BG_COLOR)
        
        self.build_ui()

    def build_ui(self):
        main_frame = tk.Frame(self.root, bg=BG_COLOR)
        main_frame.place(relx=0.5, rely=0.45, anchor="center")
        
        tk.Label(main_frame, text="[ PROFILE & SECURITY ]", font=("Consolas", 18, "bold"), bg=BG_COLOR, fg=ACCENT_PURPLE).pack(pady=(0, 20))
        
        info_frame = tk.Frame(main_frame, bg=PANEL_BG, padx=25, pady=20, relief="ridge", bd=1)
        info_frame.pack(fill="x", pady=10)
        
        tk.Label(info_frame, text=f"Account Name : {self.username}", font=("Consolas", 12), bg=PANEL_BG, fg=TEXT_COLOR).pack(anchor="w")
        tk.Label(info_frame, text=f"Assigned Role: {self.role}", font=("Consolas", 12), bg=PANEL_BG, fg=TEXT_COLOR).pack(anchor="w", pady=(10, 0))
        
        tk.Label(main_frame, text="-- Change Password --", font=("Consolas", 12, "bold"), bg=BG_COLOR, fg=ACCENT_BLUE).pack(pady=(30, 10))
        
        form_frame = tk.Frame(main_frame, bg=BG_COLOR)
        form_frame.pack()
        
        tk.Label(form_frame, text="Current Pass:", font=("Consolas", 11), bg=BG_COLOR, fg=TEXT_COLOR).grid(row=0, column=0, sticky="e", padx=10, pady=10)
        self.entry_curr = ttk.Entry(form_frame, show="*", width=30, font=("Consolas", 11), style="Normal.TEntry")
        self.entry_curr.grid(row=0, column=1, padx=10, pady=10)
        
        tk.Label(form_frame, text="New Password:", font=("Consolas", 11), bg=BG_COLOR, fg=TEXT_COLOR).grid(row=1, column=0, sticky="e", padx=10, pady=10)
        self.entry_new = ttk.Entry(form_frame, show="*", width=30, font=("Consolas", 11), style="Normal.TEntry")
        self.entry_new.grid(row=1, column=1, padx=10, pady=10)
        
        tk.Label(form_frame, text="Confirm Pass:", font=("Consolas", 11), bg=BG_COLOR, fg=TEXT_COLOR).grid(row=2, column=0, sticky="e", padx=10, pady=10)
        self.entry_conf = ttk.Entry(form_frame, show="*", width=30, font=("Consolas", 11), style="Normal.TEntry")
        self.entry_conf.grid(row=2, column=1, padx=10, pady=10)
        
        btn_frame = tk.Frame(main_frame, bg=BG_COLOR)
        btn_frame.pack(pady=30)
        
        custom_button(btn_frame, "<< BACK TO INVENTORY", self.on_back, "#555555", "#777777", width=22).pack(side="left", padx=10)
        custom_button(btn_frame, "UPDATE SECURITY", self.change_password, ACCENT_GREEN, "#2EA043", width=20).pack(side="left", padx=10)

    def change_password(self):
        curr_p, new_p, conf_p = self.entry_curr.get().strip(), self.entry_new.get().strip(), self.entry_conf.get().strip()
        if new_p != conf_p:
            messagebox.showerror("Error", "New passwords do not match.")
            return
        if len(new_p) < 8 or not re.search(r'[A-Z]', new_p) or not re.search(r'\d', new_p):
            messagebox.showwarning("Validation Error", "Password must have at least 8 chars, 1 uppercase, 1 number.")
            return
        conn = None
        try:
            conn = sqlite3.connect(DB_NAME, timeout=5)
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash FROM users WHERE username=?", (self.username,))
            row = cursor.fetchone()
            if row and bcrypt.checkpw(curr_p.encode('utf-8'), row[0].encode('utf-8')):
                hashed_new = bcrypt.hashpw(new_p.encode('utf-8'), bcrypt.gensalt())
                cursor.execute("UPDATE users SET password_hash=? WHERE username=?", (hashed_new.decode('utf-8'), self.username))
                conn.commit()
                messagebox.showinfo("Success", "Password updated successfully!")
                self.on_back()
            else:
                messagebox.showerror("Auth Error", "Incorrect Current Password.")
        finally:
            if conn: conn.close()

if __name__ == "__main__":
    #AppController()
    pass
class AuthController:
    @staticmethod
    def login_user(username, password):
        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
        row = cursor.execute("SELECT id, password_hash, role, failed_attempts, is_locked, email FROM users WHERE username=?", (username,)).fetchone()
        conn.close()
        if not row: return False, "Invalid", None, False, None
        if row[4]: return False, "Locked", None, True, None
        if bcrypt.checkpw(password.encode('utf-8'), row[1].encode('utf-8')): return True, "Success", row[2], False, row[5]
        return False, "Invalid pass", None, False, None
        
    @staticmethod
    def register_user(username, email, password, role="USER"):
        try:
            h = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode()
            conn = sqlite3.connect(DB_NAME)
            conn.execute("INSERT INTO users (username, email, password_hash, role) VALUES (?,?,?,?)", (username, email, h, role))
            conn.commit(); conn.close(); return True, "Registered"
        except: return False, "Error"
        
    @staticmethod
    def submit_password_reset_request(username, email, new_password): return True, "Requested"
    @staticmethod
    def change_password_direct(u, e, o, n): return True, "Changed"
    @staticmethod
    def get_pending_resets(): return []
    @staticmethod
    def process_bulk_resets(ids, approve): return True, "Processed"

class InventoryController:
    @staticmethod
    def get_all_items(search_text="", category="ALL"):
        conn = sqlite3.connect(DB_NAME); res = conn.execute("SELECT * FROM hardware").fetchall()
        conn.close(); return res
    @staticmethod
    def get_categories(): return []
    @staticmethod
    def get_user_loan_history(u): return []
    @staticmethod
    def get_all_loans_history(): return []
    @staticmethod
    def add_item(n, c, q, p): return True, "Added"
    @staticmethod
    def delete_bulk_items(ids): return True, "Deleted"
    @staticmethod
    def export_to_csv(u): return True, "Exported"
    @staticmethod
    def get_user_pending_borrows(u): return []

    @staticmethod
    def borrow_item(u, i, q):
        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
        name = cursor.execute("SELECT item_name FROM hardware WHERE item_id=?", (i,)).fetchone()[0]
        cursor.execute("INSERT INTO borrow_logs (item_id, item_name, username, borrowed_qty, borrow_date, status) VALUES (?, ?, ?, ?, datetime('now'), 'Pending')", (i, name, u, q))
        conn.commit(); conn.close(); return True, "Requested"

    @staticmethod
    def get_pending_borrows():
        conn = sqlite3.connect(DB_NAME); res = conn.execute("SELECT log_id, username, item_name, borrowed_qty FROM borrow_logs WHERE status='Pending'").fetchall()
        conn.close(); return res

    @staticmethod
    def process_bulk_borrows(ids, approve):
        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
        status = 'Borrowed' if approve else 'Rejected'
        for lid in ids:
            cursor.execute("UPDATE borrow_logs SET status=? WHERE log_id=?", (status, lid))
            if approve:
                item_id, qty = cursor.execute("SELECT item_id, borrowed_qty FROM borrow_logs WHERE log_id=?", (lid,)).fetchone()
                cursor.execute("UPDATE hardware SET quantity = quantity - ? WHERE item_id=?", (qty, item_id))
        conn.commit(); conn.close(); return True, "Processed"

    @staticmethod
    def get_user_active_loans(u):
        conn = sqlite3.connect(DB_NAME); res = conn.execute("SELECT log_id, item_name, borrowed_qty, borrow_date FROM borrow_logs WHERE username=? AND status='Borrowed'", (u,)).fetchall()
        conn.close(); return res

    @staticmethod
    def request_bulk_item_returns(ids):
        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
        for lid in ids: cursor.execute("UPDATE borrow_logs SET status='RETURN_PENDING' WHERE log_id=?", (lid,))
        conn.commit(); conn.close(); return True, "Return Requested"

    @staticmethod
    def get_pending_returns():
        conn = sqlite3.connect(DB_NAME); res = conn.execute("SELECT log_id, username, item_name, borrowed_qty FROM borrow_logs WHERE status='RETURN_PENDING'").fetchall()
        conn.close(); return res

    @staticmethod
    def process_bulk_returns(ids, approve):
        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
        status = 'Returned' if approve else 'Borrowed'
        for lid in ids:
            cursor.execute("UPDATE borrow_logs SET status=? WHERE log_id=?", (status, lid))
            if approve:
                item_id, qty = cursor.execute("SELECT item_id, borrowed_qty FROM borrow_logs WHERE log_id=?", (lid,)).fetchone()
                cursor.execute("UPDATE hardware SET quantity = quantity + ? WHERE item_id=?", (qty, item_id))
        conn.commit(); conn.close(); return True, "Processed"
