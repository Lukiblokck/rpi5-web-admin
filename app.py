from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import secrets, time, json, psutil, socket, subprocess

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

USER = "admin"
PASSWORD_HASH = generate_password_hash("contraseña")  # Contraseña segura

login_attempts = {}
LOCK_TIME = 300  # 5 minutos

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/", methods=["GET", "POST"])
def login():
    ip = request.remote_addr
    attempt_info = login_attempts.get(ip, {"count": 0, "time": 0})

    if attempt_info["count"] >= 5 and time.time() - attempt_info["time"] < LOCK_TIME:
        return "Demasiados intentos. Intenta más tarde.", 429

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == USER and check_password_hash(PASSWORD_HASH, password):
            session["logged_in"] = True
            login_attempts[ip] = {"count": 0, "time": 0}
            return redirect(url_for("dashboard"))
        else:
            if attempt_info["count"] >= 5:
                login_attempts[ip]["time"] = time.time()
            else:
                login_attempts[ip] = {"count": attempt_info["count"] + 1, "time": attempt_info["time"]}
            return render_template("login.html", error="Usuario o contraseña incorrectos")
    return render_template("login.html", error=None)

def check_bot_status(bot_file):
    """Revisa si un bot está corriendo por su archivo"""
    try:
        result = subprocess.run(["pgrep", "-f", bot_file], capture_output=True)
        return True if result.stdout else False
    except:
        return False

def get_rpi_info():
    """Información de la Raspberry Pi"""
    info = {
        "CPU": f"{psutil.cpu_percent()}%",
        "RAM": f"{round(psutil.virtual_memory().percent, 1)}%",
        "DISCO": f"{round(psutil.disk_usage('/').percent, 1)}%",
        "IP": socket.gethostbyname(socket.gethostname())
    }
    return info

@app.route("/dashboard")
@login_required
def dashboard():
    # Cargar bots con nombre y archivo
    with open("bots.json") as f:
        bots = json.load(f)

    # Revisar estado de cada bot por su proceso
    for bot in bots:
        bot_file = bot.get("bot_file")  # ahora usamos bot_file
        bot["status"] = "online" if check_bot_status(bot_file) else "offline"

    rpi_info = get_rpi_info()

    return render_template("dashboard.html", bots=bots, rpi_info=rpi_info)

@app.route("/logout")
@login_required
def logout():
    session["logged_in"] = False
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6060, debug=False)
