import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

# export API_KEY=pk_ff728711777149dcbb53d7bdc8574f80


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user_id = session["user_id"]

    balance = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
    cash = balance[0]["cash"]

    ownings = db.execute("SELECT symbol, share_amount FROM ownings WHERE user_id = ?", user_id)

    grand_total = cash

    for stock in ownings:
        price = lookup(stock["symbol"])["price"]
        stock_total = stock["share_amount"] * price
        stock.update({'price': price, 'stock_total': stock_total})
        grand_total += stock_total

    return render_template("index.html", ownings=ownings, cash=cash, grand_total=grand_total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    user_id = session["user_id"]

    if request.method == "POST":
        symbol = request.form.get("symbol")

        if not lookup(symbol):
            return apology("No such symbol", 400)

        bought_share = request.form.get("shares")

        if not bought_share:
            return apology("Please enter share amount", 400)

        if not (bought_share.isnumeric() and int(bought_share) > 0):
            return apology("Please enter numeric values greater than zero for share field", 400)

        current_infos = lookup(symbol)
        current_price = current_infos["price"]
        current_stock_name = current_infos["name"]
        initial_amount = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
        spent_amount = (int(bought_share) * current_price)
        # print(initial_amount)
        current_amount = initial_amount[0]["cash"] - spent_amount
        # print(str(current_amount))

        if current_amount < 0:
            return apology("Not enough money", 400)

        db.execute("UPDATE users SET cash = ? WHERE id = ?", current_amount, user_id)
        db.execute("INSERT INTO transactions (user_id, stock_symbol, current_price, total_amount, share_amount, stock_name, transaction_type) values (?, ?, ?, ?, ?, ?, ?)",
                   user_id, symbol, current_price, spent_amount, bought_share, current_stock_name, "b")

        if db.execute("SELECT COUNT(*) FROM ownings where user_id = ? AND symbol = ?", user_id, symbol)[0]["COUNT(*)"] == 0:
            db.execute("INSERT INTO ownings (user_id, share_amount, symbol) values (?, ?, ?)", user_id, bought_share, symbol)

        else:
            current_bought_share = db.execute(
                "SELECT SUM(share_amount) FROM transactions WHERE user_id = ? AND transaction_type = ? AND stock_symbol = ?", user_id, "b", symbol)
            current_sold_share = db.execute(
                "SELECT SUM(share_amount) FROM transactions WHERE user_id = ? AND transaction_type = ? AND stock_symbol = ?", user_id, "s", symbol)

            if current_sold_share[0]["SUM(share_amount)"]:
                db.execute("UPDATE ownings SET share_amount = ? WHERE user_id = ? AND symbol = ? ",
                           current_bought_share[0]["SUM(share_amount)"] - current_sold_share[0]["SUM(share_amount)"], user_id, symbol)

            else:
                db.execute("UPDATE ownings SET share_amount = ? WHERE user_id = ? AND symbol = ? ",
                           current_bought_share[0]["SUM(share_amount)"], user_id, symbol)

        return redirect("/")

    return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    user_id = session["user_id"]

    transactions = db.execute(
        "SELECT created_at, stock_symbol, share_amount, current_price, transaction_type FROM transactions WHERE user_id = ?", user_id)

    if not transactions:
        return apology("No history", 400)

    for transaction in transactions:
        if transaction["transaction_type"] == "s":
            transaction["share_amount"] = "-" + str(transaction["share_amount"])
        transaction["current_price"] = usd(transaction["current_price"])

    return render_template("history.html", transactions=transactions)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == "POST":

        symbol = request.form.get("symbol").strip()

        if not symbol:
            return apology("Symbol field can't be left empty", 400)

        if not symbol.isalpha():
            return apology("Only alphabetic characters are allowed", 400)

        stock_infos = lookup(symbol)

        if stock_infos == None:
            return apology("No such symbol", 400)

        return render_template("quoted.html", stock_infos=stock_infos)

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":

        if not request.form.get("username"):
            return apology("must provide username", 400)

            # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords do not match", 400)

        dict_to_check_username_taken = db.execute("SELECT COUNT(*) FROM users WHERE username = ?", request.form.get("username"))

        if dict_to_check_username_taken[0]["COUNT(*)"] == 1:
            return apology("username is taken", 400)

        db.execute(
            "INSERT INTO Users (username, hash) values (?, ?)", request.form.get("username"), generate_password_hash(request.form.get("password")))

        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        session["user_id"] = rows[0]["id"]

        return redirect("/")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    user_id = session["user_id"]

    available_symbols = db.execute("SELECT symbol FROM ownings WHERE user_id = ? AND share_amount > ?", user_id, 0)

    if request.method == "POST":

        current_cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)

        print(current_cash[0]["cash"])

        symbol = request.form.get("symbol")

        symbol_info = lookup(symbol)
        stock_name = symbol_info["name"]
        current_price_for_symbol = lookup(symbol)["price"]
        # print(symbol)
        # print(lookup(symbol)["price"])

        sold_shares = request.form.get("shares")

        shares_available = db.execute(
            "SELECT share_amount FROM ownings WHERE user_id = ? AND symbol = ? AND share_amount > ?", user_id, symbol, sold_shares)

        if shares_available:
            current_share_amount = shares_available[0]["share_amount"]
            db.execute("UPDATE ownings SET share_amount = ? WHERE user_id = ? AND symbol = ?",
                       current_share_amount - int(sold_shares), user_id, symbol)
            # print(current_share_amount)
            # print(current_share_amount - int(sold_shares))
            db.execute("UPDATE users SET cash = ? WHERE id = ?",
                       current_cash[0]["cash"] + (float(sold_shares) * lookup(symbol)["price"]), user_id)
            db.execute("""
                       INSERT INTO transactions (user_id, stock_symbol, total_amount, share_amount, current_price, stock_name, transaction_type)
                       VALUES (?, ?, ?, ?, ?, ?, ?)
                       """, user_id, symbol, current_price_for_symbol * float(sold_shares), sold_shares, current_price_for_symbol, stock_name, "s")

            return redirect("/")

        else:
            return apology("not enough shares", 400)

    return render_template("sell.html", available_symbols=available_symbols)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
