from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "food_ordering_secret_key_2024"

# ── In-memory data store (replace with a real DB in production) ──────────────
USERS = {
    "admin": {"password": "yashas@123", "role": "admin", "name": "yashas"},
    "user": {"password": "aditya@123",  "role": "user",  "name": "aditya"},
}

MENU = [
    {"id": 1, "name": "Margherita Pizza",   "category": "Pizza",   "price": 299, "desc": "Classic tomato, mozzarella & basil",    "emoji": "🍕", "popular": True},
    {"id": 2, "name": "Pepperoni Pizza",    "category": "Pizza",   "price": 349, "desc": "Loaded with spicy pepperoni slices",     "emoji": "🍕", "popular": True},
    {"id": 3, "name": "Veggie Burger",      "category": "Burgers", "price": 199, "desc": "Crispy patty with fresh veggies",        "emoji": "🍔", "popular": False},
    {"id": 4, "name": "Classic Burger",     "category": "Burgers", "price": 249, "desc": "Juicy beef with secret sauce",           "emoji": "🍔", "popular": True},
    {"id": 5, "name": "Caesar Salad",       "category": "Salads",  "price": 179, "desc": "Romaine, croutons & parmesan",          "emoji": "🥗", "popular": False},
    {"id": 6, "name": "Greek Salad",        "category": "Salads",  "price": 189, "desc": "Feta, olives & fresh vegetables",       "emoji": "🥗", "popular": False},
    {"id": 7, "name": "Spaghetti Bolognese","category": "Pasta",   "price": 279, "desc": "Rich meat sauce over al dente pasta",   "emoji": "🍝", "popular": True},
    {"id": 8, "name": "Penne Arrabbiata",   "category": "Pasta",   "price": 249, "desc": "Spicy tomato sauce with garlic",        "emoji": "🍝", "popular": False},
    {"id": 9, "name": "Chocolate Lava Cake","category": "Desserts","price": 149, "desc": "Warm cake with molten chocolate center","emoji": "🍫", "popular": True},
    {"id":10, "name": "Cheesecake",         "category": "Desserts","price": 139, "desc": "New York style with berry compote",     "emoji": "🍰", "popular": False},
    {"id":11, "name": "Cold Coffee",        "category": "Drinks",  "price":  99, "desc": "Chilled espresso with milk & cream",    "emoji": "☕", "popular": True},
    {"id":12, "name": "Fresh Lime Soda",    "category": "Drinks",  "price":  79, "desc": "Zesty lime with sparkling water",       "emoji": "🥤", "popular": False},
]

ORDERS = []          # list of order dicts
ORDER_COUNTER = [1]  # mutable counter

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_order_by_id(oid):
    return next((o for o in ORDERS if o["id"] == oid), None)

def login_required(role=None):
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "username" not in session:
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return wrapper
    return decorator

# ── Auth routes ───────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    if "username" not in session:
        return redirect(url_for("login"))
    if session["role"] == "admin":
        return redirect(url_for("admin_dashboard"))
    return redirect(url_for("menu"))

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username    = request.form.get("username", "").strip()
        password    = request.form.get("password", "").strip()
        selected_role = request.form.get("role", "user").strip()
        user = USERS.get(username)
        if user and user["password"] == password:
            if user["role"] != selected_role:
                role_label = "Admin" if selected_role == "admin" else "Customer"
                error = f"This account is not registered as {role_label}. Please select the correct role."
            else:
                session["username"] = username
                session["role"]     = user["role"]
                session["name"]     = user["name"]
                session["cart"]     = []
                return redirect(url_for("index"))
        elif not error:
            error = "Invalid username or password."
    return render_template("login.html", error=error)

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        name     = request.form.get("name", "").strip()
        if username in USERS:
            error = "Username already exists."
        elif not username or not password or not name:
            error = "All fields are required."
        else:
            USERS[username] = {"password": password, "role": "user", "name": name}
            session["username"] = username
            session["role"]     = "user"
            session["name"]     = name
            session["cart"]     = []
            return redirect(url_for("menu"))
    return render_template("register.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ── User routes ───────────────────────────────────────────────────────────────

@app.route("/menu")
@login_required()
def menu():
    categories = sorted(set(item["category"] for item in MENU))
    return render_template("menu.html", menu=MENU, categories=categories,
                           cart=session.get("cart", []))

@app.route("/cart/add", methods=["POST"])
@login_required()
def add_to_cart():
    item_id = int(request.json.get("id"))
    item    = next((i for i in MENU if i["id"] == item_id), None)
    if not item:
        return jsonify({"success": False})
    cart = session.get("cart", [])
    existing = next((c for c in cart if c["id"] == item_id), None)
    if existing:
        existing["qty"] += 1
    else:
        cart.append({"id": item_id, "name": item["name"],
                     "price": item["price"], "qty": 1, "emoji": item["emoji"]})
    session["cart"] = cart
    session.modified = True
    total_items = sum(c["qty"] for c in cart)
    return jsonify({"success": True, "cart_count": total_items})

@app.route("/cart/remove", methods=["POST"])
@login_required()
def remove_from_cart():
    item_id = int(request.json.get("id"))
    cart = session.get("cart", [])
    cart = [c for c in cart if c["id"] != item_id]
    session["cart"] = cart
    session.modified = True
    return jsonify({"success": True, "cart_count": sum(c["qty"] for c in cart)})

@app.route("/cart/update", methods=["POST"])
@login_required()
def update_cart():
    item_id = int(request.json.get("id"))
    qty     = int(request.json.get("qty", 1))
    cart = session.get("cart", [])
    for c in cart:
        if c["id"] == item_id:
            c["qty"] = max(1, qty)
    session["cart"] = cart
    session.modified = True
    return jsonify({"success": True})

@app.route("/cart")
@login_required()
def cart():
    cart_items = session.get("cart", [])
    total = sum(c["price"] * c["qty"] for c in cart_items)
    return render_template("cart.html", cart=cart_items, total=total)

@app.route("/checkout", methods=["POST"])
@login_required()
def checkout():
    cart_items = session.get("cart", [])
    if not cart_items:
        return redirect(url_for("cart"))
    address  = request.form.get("address", "").strip()
    phone    = request.form.get("phone", "").strip()
    payment  = request.form.get("payment", "COD")
    if not address or not phone:
        return redirect(url_for("cart"))
    total = sum(c["price"] * c["qty"] for c in cart_items)
    order = {
        "id":         ORDER_COUNTER[0],
        "username":   session["username"],
        "name":       session["name"],
        "order_items": list(cart_items),
        "total":      total,
        "address":    address,
        "phone":      phone,
        "payment":    payment,
        "status":     "Placed",
        "created_at": datetime.now().strftime("%d %b %Y, %I:%M %p"),
    }
    ORDERS.append(order)
    ORDER_COUNTER[0] += 1
    session["cart"] = []
    session.modified = True
    return redirect(url_for("order_success", order_id=order["id"]))

@app.route("/order/success/<int:order_id>")
@login_required()
def order_success(order_id):
    order = get_order_by_id(order_id)
    return render_template("order_success.html", order=order)

@app.route("/orders")
@login_required()
def my_orders():
    user_orders = [o for o in ORDERS if o["username"] == session["username"]]
    user_orders.sort(key=lambda x: x["id"], reverse=True)
    return render_template("my_orders.html", orders=user_orders)

# ── Admin routes ──────────────────────────────────────────────────────────────

@app.route("/admin")
@login_required(role="admin")
def admin_dashboard():
    total_orders   = len(ORDERS)
    total_revenue  = sum(o["total"] for o in ORDERS)
    pending_orders = sum(1 for o in ORDERS if o["status"] == "Placed")
    recent_orders  = sorted(ORDERS, key=lambda x: x["id"], reverse=True)[:5]
    return render_template("admin_dashboard.html",
                           total_orders=total_orders,
                           total_revenue=total_revenue,
                           pending_orders=pending_orders,
                           recent_orders=recent_orders,
                           total_users=len(USERS))

@app.route("/admin/orders")
@login_required(role="admin")
def admin_orders():
    all_orders = sorted(ORDERS, key=lambda x: x["id"], reverse=True)
    return render_template("admin_orders.html", orders=all_orders)

@app.route("/admin/orders/update", methods=["POST"])
@login_required(role="admin")
def update_order_status():
    order_id = int(request.json.get("id"))
    status   = request.json.get("status")
    order    = get_order_by_id(order_id)
    if order:
        order["status"] = status
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route("/admin/menu")
@login_required(role="admin")
def admin_menu():
    categories = sorted(set(item["category"] for item in MENU))
    return render_template("admin_menu.html", menu=MENU, categories=categories)

@app.route("/admin/menu/add", methods=["POST"])
@login_required(role="admin")
def add_menu_item():
    new_id = max(i["id"] for i in MENU) + 1
    MENU.append({
        "id":       new_id,
        "name":     request.form.get("name"),
        "category": request.form.get("category"),
        "price":    int(request.form.get("price", 0)),
        "desc":     request.form.get("desc"),
        "emoji":    request.form.get("emoji", "🍽️"),
        "popular":  request.form.get("popular") == "on",
    })
    return redirect(url_for("admin_menu"))

@app.route("/admin/menu/delete/<int:item_id>", methods=["POST"])
@login_required(role="admin")
def delete_menu_item(item_id):
    global MENU
    MENU = [i for i in MENU if i["id"] != item_id]
    return jsonify({"success": True})

@app.route("/admin/users")
@login_required(role="admin")
def admin_users():
    users_list = [{"username": k, "name": v["name"], "role": v["role"]}
                  for k, v in USERS.items()]
    return render_template("admin_users.html", users=users_list)

if __name__ == "__main__":
    app.run(debug=True, port=5000)