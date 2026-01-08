import socket
import threading
import time
from datetime import datetime

HOST = "127.0.0.1"
PORT = 9090
BUFFER = 1024

clients = {}
connection_order = []
muted_users = {}
admin_username = None
server_start_time = time.time()

lock = threading.Lock()


def now():
    return datetime.now().strftime("%H:%M:%S")


def safe_send(sock, msg):
    try:
        sock.sendall(msg.encode())
        return True
    except:
        return False


# --- התיקון החשוב נמצא כאן ---
def broadcast(msg):
    # קודם כל מעתיקים את הרשימה ומשחררים את המנעול
    # זה מונע מהשרת להיתקע אם משתמש אחד מתנתק בפתאומיות
    with lock:
        active_clients = list(clients.items())

    dead = []
    for u, s in active_clients:
        if not safe_send(s, msg):
            dead.append(u)

    for u in dead:
        cleanup_user(u)


# -----------------------------

def promote_new_admin():
    global admin_username
    if connection_order:
        admin_username = connection_order[0]
        # בדיקה שהמשתמש עדיין קיים לפני שליחה
        if admin_username in clients:
            safe_send(clients[admin_username], f"[{now()}] You are now the administrator.\n")
        broadcast(f"[{now()}] {admin_username} is now the administrator.\n")
    else:
        admin_username = None


def cleanup_user(username):
    global admin_username

    # שימוש במנעול כדי למנוע התנגשויות בעת מחיקה
    with lock:
        if username not in clients: return
        sock = clients.pop(username, None)
        if username in muted_users: muted_users.pop(username, None)
        if username in connection_order: connection_order.remove(username)

    if sock:
        try:
            sock.close()
        except:
            pass

    if username == admin_username:
        promote_new_admin()


def process_message(sock, current_username, msg):
    global admin_username

    if msg == "/quit":
        safe_send(sock, "[SERVER] You disconnected.\n")
        raise Exception("Quit")

    if msg == "/ping":
        safe_send(sock, "Pong\n")
        return current_username

    if msg == "/uptime":
        seconds = int(time.time() - server_start_time)
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        safe_send(sock, f"[SERVER] Server Uptime: {h:02d}:{m:02d}:{s:02d}\n")
        return current_username

    if msg == "/users":
        with lock:  # נועלים רק לשבריר שנייה לקריאת הרשימה
            users = list(clients.keys())
            admin = admin_username
        text = "\n".join(f"- {u}" + (" (Admin)" if u == admin else "") for u in users)
        safe_send(sock, f"Connected users:\n{text}\n")
        return current_username

    if msg == "/admin":
        safe_send(sock, f"Admin: {admin_username}\n")
        return current_username

    if msg == "/whoami":
        role = "Administrator" if current_username == admin_username else "Regular user"
        safe_send(sock, f"You are: {current_username}\nRole: {role}\n")
        return current_username

    if msg.startswith("/rename"):
        parts = msg.split(maxsplit=1)
        if len(parts) != 2: return current_username
        new_name = parts[1].strip()

        with lock:
            if new_name in clients:
                safe_send(sock, f"[ERROR] The name '{new_name}' is already taken.\n")
                return current_username

            clients[new_name] = clients.pop(current_username)
            if current_username in connection_order:
                connection_order[connection_order.index(current_username)] = new_name
            if current_username == admin_username:
                admin_username = new_name

            old_name = current_username
            current_username = new_name

        broadcast(f"[{now()}] {old_name} changed name to {new_name}.\n")
        return current_username

    if msg.startswith("@"):
        try:
            target_name, text = msg[1:].split(" ", 1)

            # שליפה בטוחה של הסוקט
            target_sock = None
            with lock:
                target_sock = clients.get(target_name)

            if target_sock:
                safe_send(target_sock, f"[{now()}] [PM from {current_username}] {text}\n")
                if target_name != current_username:
                    safe_send(sock, f"[{now()}] [PM to {target_name}] {text}\n")
            else:
                safe_send(sock, f"[ERROR] User '{target_name}' not found.\n")
        except:
            safe_send(sock, "[ERROR] Usage: @username message\n")
        return current_username

    if msg.startswith("/calc"):
        parts = msg.split()
        if len(parts) == 4:
            try:
                a, op, b = float(parts[1]), parts[2], float(parts[3])
                res = "Err"
                if op == "+":
                    res = a + b
                elif op == "-":
                    res = a - b
                elif op == "*":
                    res = a * b
                elif op == "/":
                    res = a / b if b != 0 else "DivZero"
                safe_send(sock, f"[CALC] {a} {op} {b} = {res}\n")
            except:
                pass
        return current_username

    if msg.startswith("/mute") or msg.startswith("/unmute"):
        if current_username != admin_username:
            safe_send(sock, "[ERROR] Admin only.\n")
            return current_username

        parts = msg.split(maxsplit=1)
        if len(parts) < 2: return current_username
        target = parts[1]

        if msg.startswith("/mute"):
            # בדיקה האם המשתמש קיים נעשית עם מנעול
            exists = False
            with lock:
                exists = target in clients

            if exists and target != admin_username:
                muted_users[target] = None
                broadcast(f"[{now()}] {target} has been muted.\n")
        elif msg.startswith("/unmute"):
            if target in muted_users:
                muted_users.pop(target)
                broadcast(f"[{now()}] {target} has been unmuted.\n")
        return current_username

    if current_username in muted_users:
        safe_send(sock, "[SYSTEM] You are muted.\n")
        return current_username

    broadcast(f"[{now()}] {current_username}: {msg}\n")
    return current_username


def handle_client(sock):
    global admin_username
    username = None
    buffer = ""

    try:
        while True:
            data = sock.recv(BUFFER)
            if not data: return
            temp_name = data.decode().strip()

            # בדיקת שם פנוי
            with lock:
                if temp_name in clients:
                    safe_send(sock, "TAKEN")
                else:
                    safe_send(sock, "OK")
                    username = temp_name
                    clients[username] = sock
                    connection_order.append(username)
                    # יציאה מהלולאה רק אם הכל תקין
                    break

                    # הקצאת אדמין
        with lock:
            if admin_username is None:
                admin_username = username
                safe_send(sock, f"[{now()}] You are the administrator.\n")

        safe_send(sock, f"[{now()}] Welcome {username}!\n")
        broadcast(f"[{now()}] {username} joined the chat.\n")

        # לולאת ההודעות
        while True:
            data = sock.recv(BUFFER)
            if not data: break
            buffer += data.decode()

            while "\n" in buffer:
                msg, buffer = buffer.split("\n", 1)
                msg = msg.strip()
                if not msg: continue
                username = process_message(sock, username, msg)

    except:
        pass
    finally:
        if username:
            cleanup_user(username)
            # משדרים ניתוק רק אם המשתמש באמת היה מחובר
            broadcast(f"[{now()}] {username} disconnected.\n")
        else:
            try:
                sock.close()
            except:
                pass


def start_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # תיקון: מאפשר להריץ את השרת מחדש על אותו פורט מיד לאחר סגירה
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen()
    print(f"Server started on {HOST}:{PORT}")
    while True:
        c, _ = s.accept()
        threading.Thread(target=handle_client, args=(c,), daemon=True).start()


if __name__ == "__main__":
    start_server()