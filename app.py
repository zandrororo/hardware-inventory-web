# ==========================================================
# CAMPUS HARDWARE INVENTORY SYSTEM
# Flask Web Application
# ==========================================================
#
# This file connects the web browser to the existing
# Laboratorysystem.py.
#
# The original database and controller functions are reused.
# ==========================================================

# ==========================================================
# 1. IMPORT FLASK TOOLS
# ==========================================================
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_file
)

# Used to create login/admin protection decorators.
from functools import wraps

# Used for environment variables and file paths.
import os

# ==========================================================
# 2. IMPORT THE ORIGINAL PYTHON SYSTEM
# ==========================================================

# We reuse the existing database and controllers.
from Laboratorysystem import (
    init_db,
    AuthController,
    InventoryController
)

# ==========================================================
# 3. CREATE THE FLASK APPLICATION
# ==========================================================

app = Flask(__name__)

# Secret key is required for Flask sessions.
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "lab1-development-secret-change-me"
)
# ==========================================================
# 4. LOGIN REQUIRED DECORATOR
# ==========================================================
#
# This checks if the user is logged in before accessing
# protected pages.
# ==========================================================
def login_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        # If there is no username in the session,
        # the user is not logged in.
        if "username" not in session:

            flash(
                "Please log in first.",
                "warning"
            )

            return redirect(
                url_for("login")
            )

        return view(*args, **kwargs)

    return wrapped
# ==========================================================
# 5. ADMIN REQUIRED DECORATOR
# ==========================================================
#
# This allows only ADMIN accounts to access admin functions.
# ==========================================================
def admin_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        # Check the user's role.
        if session.get("role") != "ADMIN":

            flash(
                "Administrator access required.",
                "danger"
            )

            return redirect(
                url_for("dashboard")
            )

        return view(*args, **kwargs)

    return wrapped


# ==========================================================
# 6. HOME / INDEX ROUTE
# ==========================================================
#
# "/" is the starting address of the web application.
# ==========================================================
@app.route("/")
def index():

    # If the user is already logged in,
    # go to the dashboard.
    if "username" in session:

        return redirect(
            url_for("dashboard")
        )

    # Otherwise, show the login page.
    return redirect(
        url_for("login")
    )
# ==========================================================
# 7. LOGIN ROUTE
# ==========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    # GET = display the login page.
    # POST = process the login form.
    if request.method == "POST":

        # Get the values entered by the user.
        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()

        # Make sure both fields have values.
        if not username or not password:

            flash(
                "Username and password are required.",
                "danger"
            )

            return render_template(
                "login.html"
            )

        # Use the existing authentication controller.
        ok, msg, role, is_locked, email = (
            AuthController.login_user(
                username,
                password
            )
        )

        # Login successful.
        if ok:

            # Remove any previous session data.
            session.clear()

            # Save the user's information in the session.
            session["username"] = username
            session["role"] = role.upper()
            session["email"] = email

            flash(
                msg,
                "success"
            )

            return redirect(
                url_for("dashboard")
            )

        # Login failed.
        flash(
            msg,
            "danger"
        )

        # Return to the login page.
        return render_template(
            "login.html",
            locked=is_locked,
            locked_username=username
        )

    # Display the login page.
    return render_template(
        "login.html"
    )
# ==========================================================
# 8. REGISTRATION ROUTE
# ==========================================================
@app.route("/register", methods=["GET", "POST"])
def register():

    # GET = display registration page.
    if request.method == "GET":

        return render_template(
            "register.html"
        )

    # Get registration information.
    username = request.form.get(
        "username",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    ).strip()

    role = request.form.get(
        "role",
        "USER"
    ).strip().upper()

    # Only USER and ADMIN are accepted.
    if role not in ("USER", "ADMIN"):

        role = "USER"

    # Check required fields.
    if not username or not email or not password:

        flash(
            "All registration fields are required.",
            "danger"
        )

        return redirect(
            url_for("login")
        )

    # Use the original registration function.
    ok, msg = AuthController.register_user(
        username,
        email,
        password,
        role=role
    )

    # Show the result.
    flash(
        msg,
        "success" if ok else "warning"
    )

    return redirect(
        url_for("login")
    )
# ==========================================================
# 9. PASSWORD RESET REQUEST
# ==========================================================
@app.route(
    "/reset-request",
    methods=["GET", "POST"]
)
def reset_request():

    # GET = display reset page.
    if request.method == "GET":

        return render_template(
            "reset.html"
        )

    # Get reset information.
    username = request.form.get(
        "username",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip()

    new_password = request.form.get(
        "new_password",
        ""
    ).strip()

    confirm_password = request.form.get(
        "confirm_password",
        ""
    ).strip()

    # Check required fields.
    if (
        not username
        or not email
        or not new_password
        or not confirm_password
    ):

        flash(
            "All reset fields are required.",
            "danger"
        )

        return redirect(
            url_for("login")
        )

    # Check if passwords match.
    if new_password != confirm_password:

        flash(
            "New passwords do not match.",
            "danger"
        )

        return redirect(
            url_for("login")
        )

    # Use the original password reset function.
    ok, msg = (
        AuthController.submit_password_reset_request(
            username,
            email,
            new_password
        )
    )

    flash(
        msg,
        "success" if ok else "danger"
    )

    return redirect(
        url_for("login")
    )
# ==========================================================
# 10. DASHBOARD ROUTE
# ==========================================================
@app.route("/dashboard")
@login_required
def dashboard():

    # Get search text from the browser.
    search = request.args.get(
        "search",
        ""
    ).strip()

    # Get selected category.
    category = request.args.get(
        "category",
        "ALL"
    )

    # Use ALL when no category was selected.
    if not category:

        category = "ALL"

    # Get inventory based on search/filter.
    items = InventoryController.get_all_items(
        search_text=search,
        category=category
    )

    # Get all available categories.
    categories = InventoryController.get_categories()
    # ======================================================
    # TOTAL STOCKS
    # ======================================================
    #
    # Get ALL inventory records so that Total Stocks
    # is not affected by the search box or category filter.
    # ======================================================
    all_items_for_total = (
        InventoryController.get_all_items(
            search_text="",
            category="ALL"
        )
    )

    # Add all stock quantities.
    total_stocks = sum(
        item[3]
        for item in all_items_for_total
    )
    # ======================================================
    # CREATE EMPTY DATA LISTS
    # ======================================================

    active_loans = []
    history = []
    pending_returns = []
    pending_borrows = []
    pending_borrow_requests = []
    all_loans = []
    pending_resets = []
    # ======================================================
    # USER DATA
    # ======================================================
    if session["role"] == "USER":

        # Items currently borrowed by the user.
        active_loans = (
            InventoryController.get_user_active_loans(
                session["username"]
            )
        )

        # Borrow requests waiting for admin approval.
        pending_borrow_requests = (
            InventoryController.get_user_pending_borrows(
                session["username"]
            )
        )

        # User's borrowing history.
        history = (
            InventoryController.get_user_loan_history(
                session["username"]
            )
        )
    # ======================================================
    # ADMIN DATA
    # ======================================================
    else:

        # Returns waiting for admin approval.
        pending_returns = (
            InventoryController.get_pending_returns()
        )

        # Borrow requests waiting for approval.
        pending_borrows = (
            InventoryController.get_pending_borrows()
        )

        # Complete borrowing history.
        all_loans = (
            InventoryController.get_all_loans_history()
        )

        # Password reset requests.
        pending_resets = (
            AuthController.get_pending_resets()
        )
    # ======================================================
    # SEND DATA TO dashboard.html
    # ======================================================

    return render_template(
        "dashboard.html",

        items=items,

        categories=categories,

        search=search,

        selected_category=category,

        total_stocks=total_stocks,

        active_loans=active_loans,

        history=history,

        pending_returns=pending_returns,

        pending_borrows=pending_borrows,

        pending_borrow_requests=(
            pending_borrow_requests
        ),

        all_loans=all_loans,

        pending_resets=pending_resets
    )
# ==========================================================
# 11. BORROW ITEM (UPDATED FOR MULTIPLE SELECTION)
# ==========================================================
@app.route("/borrow", methods=["POST"])
@login_required
def borrow():
    # Only USER accounts can borrow.
    if session["role"] != "USER":
        flash("Only USER accounts can borrow equipment.", "danger")
        return redirect(url_for("dashboard"))

    # Kunin lahat ng chineck na items gamit ang getlist
    raw_ids = request.form.getlist("item_id")
    
    if not raw_ids:
        flash("Please select at least one item to borrow.", "warning")
        return redirect(url_for("dashboard"))

    success_count = 0
    for item_id_str in raw_ids:
        try:
            item_id = int(item_id_str)
            # Kunin ang specific na quantity para sa item na ito
            quantity = int(request.form.get(f"quantity_{item_id}", "1"))
            
            if quantity >= 1:
                ok, msg = InventoryController.borrow_item(session["username"], item_id, quantity)
                if ok:
                    success_count += 1
        except ValueError:
            continue

    if success_count > 0:
        flash(f"Successfully requested {success_count} item(s). Pending admin approval.", "success")
    else:
        flash("Failed to request items. Invalid input.", "danger")

    return redirect(url_for("dashboard"))
# ==========================================================
# 12. REQUEST RETURN
# ==========================================================
@app.route(
    "/return-request",
    methods=["POST"]
)
@login_required
def return_request():

    # Get selected loan IDs.
    raw_ids = request.form.getlist(
        "loan_ids"
    )

    try:

        loan_ids = [
            int(x)
            for x in raw_ids
        ]

    except ValueError:

        loan_ids = []

    # Only USER accounts can request returns.
    if session["role"] != "USER":

        flash(
            "Only USER accounts can request returns.",
            "danger"
        )

        return redirect(
            url_for("dashboard")
        )

    # Use the existing return function.
    ok, msg = (
        InventoryController.request_bulk_item_returns(
            loan_ids
        )
    )

    flash(
        msg,
        "success" if ok else "warning"
    )

    return redirect(
        url_for("dashboard")
    )
# ==========================================================
# 13. CHANGE PASSWORD
# ==========================================================
@app.route(
    "/change-password",
    methods=["POST"]
)
@login_required
def change_password():

    # Get current and new passwords.
    old_password = request.form.get(
        "old_password",
        ""
    )

    new_password = request.form.get(
        "new_password",
        ""
    )

    # Both fields are required.
    if not old_password or not new_password:

        flash(
            "Both current and new passwords are required.",
            "danger"
        )

        return redirect(
            url_for("dashboard")
        )

    # Use the existing password function.
    ok, msg = AuthController.change_password_direct(
        session["username"],
        session.get("email", ""),
        old_password,
        new_password
    )

    flash(
        msg,
        "success" if ok else "danger"
    )

    return redirect(
        url_for("dashboard")
    )
# ==========================================================
# 14. ADMIN - ADD HARDWARE
# ==========================================================
@app.route(
    "/admin/add",
    methods=["POST"]
)
@admin_required
def admin_add():

    # Get hardware information.
    try:

        name = request.form.get(
            "item_name",
            ""
        ).strip()

        category = request.form.get(
            "category",
            ""
        ).strip()

        quantity = int(
            request.form.get(
                "quantity",
                ""
            )
        )

        unit_price = float(
            request.form.get(
                "unit_price",
                ""
            )
        )

    except ValueError:

        flash(
            "Quantity must be an integer and unit price must be numeric.",
            "danger"
        )

        return redirect(
            url_for("dashboard")
        )

    # Use the original add_item function.
    ok, msg = InventoryController.add_item(
        name,
        category,
        quantity,
        unit_price
    )

    flash(
        msg,
        "success" if ok else "danger"
    )

    return redirect(
        url_for("dashboard")
    )
# ==========================================================
# 15. ADMIN - DELETE HARDWARE
# ==========================================================
@app.route(
    "/admin/delete",
    methods=["POST"]
)
@admin_required
def admin_delete():

    # Get selected hardware IDs.
    raw_ids = request.form.getlist(
        "item_ids"
    )

    try:

        item_ids = [
            int(x)
            for x in raw_ids
        ]

    except ValueError:

        item_ids = []

    # Delete selected items.
    ok, msg = InventoryController.delete_bulk_items(
        item_ids
    )

    flash(
        msg,
        "success" if ok else "warning"
    )

    return redirect(
        url_for("dashboard")
    )
# ==========================================================
# ADMIN - UPDATE HARDWARE (NEW FOR LAB 8)
# ==========================================================
@app.route("/admin/update", methods=["POST"])
@admin_required
def admin_update():
    try:
        item_id = int(request.form.get("item_id"))
        name = request.form.get("item_name", "").strip()
        category = request.form.get("category", "").strip()
        quantity = int(request.form.get("quantity", ""))
        unit_price = float(request.form.get("unit_price", ""))

        # Dynamic stock logic equivalent sa desktop app
        if quantity == 0: 
            status = 'Out of Stock'
        elif 1 <= quantity <= 5: 
            status = 'Low Stock'
        elif 6 <= quantity <= 10: 
            status = 'Mid Stock'
        else: 
            status = 'High Stock'

        import sqlite3
        from Laboratorysystem import DB_NAME
        
        conn = sqlite3.connect(DB_NAME, timeout=5)
        cursor = conn.cursor()
        cursor.execute("UPDATE hardware SET item_name=?, category=?, quantity=?, unit_price=?, status=? WHERE item_id=?",
                       (name, category, quantity, unit_price, status, item_id))
        conn.commit()
        conn.close()

        flash(f"Item '{name}' updated successfully!", "success")
    except Exception as e:
        flash("Error updating item. Check your inputs.", "danger")

    return redirect(url_for("dashboard"))
# ==========================================================
# 16. ADMIN - BORROW APPROVAL
# ==========================================================
@app.route(
    "/admin/borrow-action",
    methods=["POST"]
)
@admin_required
def admin_borrow_action():

    # Get selected borrow request IDs.
    raw_ids = request.form.getlist(
        "loan_ids"
    )

    # Approve when the form action is "approve".
    approve = (
        request.form.get("action")
        == "approve"
    )

    try:

        loan_ids = [
            int(x)
            for x in raw_ids
        ]

    except ValueError:

        loan_ids = []

    # Process the borrow requests.
    ok, msg = (
        InventoryController.process_bulk_borrows(
            loan_ids,
            approve=approve
        )
    )

    flash(
        msg,
        "success" if ok else "danger"
    )

    return redirect(
        url_for("dashboard")
    )
# ==========================================================
# 17. ADMIN - RETURN APPROVAL
# ==========================================================
@app.route(
    "/admin/return-action",
    methods=["POST"]
)
@admin_required
def admin_return_action():

    # Get selected return request IDs.
    raw_ids = request.form.getlist(
        "loan_ids"
    )

    # Check whether Admin approved the return.
    approve = (
        request.form.get("action")
        == "approve"
    )

    try:

        loan_ids = [
            int(x)
            for x in raw_ids
        ]

    except ValueError:

        loan_ids = []

    # Process return requests.
    ok, msg = (
        InventoryController.process_bulk_returns(
            loan_ids,
            approve=approve
        )
    )

    flash(
        msg,
        "success" if ok else "danger"
    )

    return redirect(
        url_for("dashboard")
    )
# ==========================================================
# 18. ADMIN - PASSWORD RESET APPROVAL
# ==========================================================
@app.route(
    "/admin/reset-action",
    methods=["POST"]
)
@admin_required
def admin_reset_action():

    # Get selected reset request IDs.
    raw_ids = request.form.getlist(
        "request_ids"
    )

    # Check whether Admin approved the reset.
    approve = (
        request.form.get("action")
        == "approve"
    )

    try:

        request_ids = [
            int(x)
            for x in raw_ids
        ]

    except ValueError:

        request_ids = []

    # Process reset requests.
    ok, msg = (
        AuthController.process_bulk_resets(
            request_ids,
            approve=approve
        )
    )

    flash(
        msg,
        "success" if ok else "danger"
    )

    return redirect(
        url_for("dashboard")
    )
# ==========================================================
# 19. EXPORT INVENTORY REPORT
# ==========================================================
@app.route("/export")
@login_required
def export():

    # Create the CSV report using the existing controller.
    ok, msg = InventoryController.export_to_csv(
        session["username"]
    )

    # If export failed, return to dashboard.
    if not ok:

        flash(
            msg,
            "danger"
        )

        return redirect(
            url_for("dashboard")
        )

    # Get the CSV file path.
    path = os.path.abspath(
        "inventory_report.csv"
    )

    # Make sure the file exists.
    if not os.path.exists(path):

        flash(
            "The CSV report could not be found.",
            "danger"
        )

        return redirect(
            url_for("dashboard")
        )

    # Send the CSV file to the browser.
    return send_file(
        path,
        as_attachment=True,
        download_name="inventory_report.csv"
    )
# ==========================================================
# 20. LOGOUT
# ==========================================================
@app.route("/logout")
def logout():

    # Remove the user's session.
    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("login")
    )
# ==========================================================
# 21. START THE FLASK WEB SERVER
# ==========================================================
if __name__ == "__main__":

    # Initialize the existing database.
    init_db()

    print()
    print("=" * 58)
    print(" CAMPUS HARDWARE INVENTORY - WEB PORTAL")
    print("=" * 58)
    print()

    print(" Open Google Chrome and go to:")
    print(" http://127.0.0.1:5000")

    print()
    print(" Press CTRL+C to stop the server.")
    print("=" * 58)
    print()

    # Start Flask.
    app.run(debug=True)
