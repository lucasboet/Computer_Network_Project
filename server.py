import socket
import threading
import time
from datetime import datetime

HOST = "127.0.0.1"
PORT = 9090
BUFFER = 1024

clients = {}  # username -> socket
connection_order = []  # join order (to track admin)
muted_users = {}  # username -> mute_end_time
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


def broadcast(msg):
    dead = []
    with lock:
        for u, s in clients.items():
            if not safe_send(s, msg):
                dead.append(u)
    for u in dead:
        cleanup_user(u)


def promote_new_admin():
    global admin_username
    if connection_order:
        admin_username = connection_order[0]
        safe_send(clients[admin_username], f"[{now()}] You are now the administrator.\n")
        broadcast(f"[{now()}] {admin_username} is now the administrator.\n")
    else:
        admin_username = None


def cleanup_user(username):
    global admin_username
    if username not in clients: return

    sock = clients.pop(username, None)
    muted_users.pop(username, None)

    if username in connection_order:
        connection_order.remove(username)

    if sock:
        try:
            sock.close()
        except:
            pass

    if username == admin_username:
        promote_new_admin()


def is_muted(username):
    if username not in muted_users: return False
    end = muted_users[username]
    if end is None: return True
    if time.time() < end: return True
    muted_users.pop(username)
    broadcast(f"[{now()}] {username} is no longer muted.\n")
    return False


# --- הלוגיקה שתוקנה נמצאת כאן ---
def process_message(sock, current_username, msg):
    global admin_username

    # 1. Quit
    if msg == "/quit":
        safe_send(sock, "[SERVER] You disconnected.\n")
        raise Exception("Quit")

    # 2. Commands that don't change state
    if msg == "/ping":
        safe_send(sock, "Pong\n")
        return current_username  # מחזיר את השם הקיים

    if msg == "/uptime":
        uptime = int(time.time() - server_start_time)
        safe_send(sock, f"Uptime: {uptime}s\n")
        return current_username

    if msg == "/users":
        with lock:
            users = list(clients.keys())
            admin = admin_username
        text = "\n".join(f"- {u}" + (" (Admin)" if u == admin else "") for u in users)
        safe_send(sock, f"Connected users:\n{text}\n")
        return current_username

    if msg == "/admin":
        safe_send(sock, f"Admin: {admin_username}\n")
        return current_username

    if msg == "/whoami":
        # עכשיו זה ישתמש בשם המעודכן!
        role = "Administrator" if current_username == admin_username else "Regular user"
        muted = "Yes" if current_username in muted_users else "No"
        safe_send(sock, f"You are: {current_username}\nRole: {role}\nMuted: {muted}\n")
        return current_username

    # 3. Rename Logic (The Fix)
    if msg.startswith("/rename"):
        parts = msg.split(maxsplit=1)
        if len(parts) != 2: return current_username
        new_name = parts[1].strip()
        if not new_name: return current_username

        with lock:
            if new_name in clients:
                safe_send(sock, "[ERROR] Username already taken.\n")
                return current_username

            # Update Data Structures
            clients[new_name] = clients.pop(current_username)
            if current_username in connection_order:
                connection_order[connection_order.index(current_username)] = new_name
            if current_username in muted_users:
                muted_users[new_name] = muted_users.pop(current_username)

            # Update Admin
            if current_username == admin_username:
                admin_username = new_name

            old_name = current_username
            current_username = new_name  # מעדכן מקומית

        broadcast(f"[{now()}] {old_name} changed name to {new_name}.\n")
        return current_username  # מחזיר את השם החדש ללולאה הראשית!

    # 4. Admin Commands
    if msg.startswith("/mute"):
        if current_username != admin_username:
            safe_send(sock, "[ERROR] Admin only.\n")
            return current_username
        parts = msg.split()
        if len(parts) >= 2:
            target = parts[1]
            if target in clients and target != admin_username:
                muted_users[target] = None  # Permanent by default
                broadcast(f"[{now()}] {target} muted by admin.\n")
        return current_username

    if msg.startswith("/unmute"):
        if current_username != admin_username: return current_username
        parts = msg.split()
        if len(parts) == 2:
            target = parts[1]
            if target in muted_users:
                muted_users.pop(target)
                broadcast(f"[{now()}] {target} unmuted by admin.\n")
        return current_username

    # 5. Normal Chat
    if is_muted(current_username):
        safe_send(sock, "You are muted.\n")
        return current_username

    broadcast(f"[{now()}] {current_username}: {msg}\n")
    return current_username


def handle_client(sock):
    global admin_username
    username = None
    buffer = ""

    try:
        safe_send(sock, "Enter username: ")

        # Registration
        while True:
            data = sock.recv(BUFFER)
            if not data: return
            temp = data.decode().strip()
            if not temp: continue

            with lock:
                if temp in clients:
                    safe_send(sock, "Username taken, try again: ")
                else:
                    username = temp
                    clients[username] = sock
                    connection_order.append(username)
                    break

        with lock:
            if admin_username is None:
                admin_username = username
                safe_send(sock, f"[{now()}] You are the administrator.\n")

        safe_send(sock, f"[{now()}] Welcome {username}!\n")
        broadcast(f"[{now()}] {username} joined the chat.\n")

        # Main Loop
        while True:
            try:
                data = sock.recv(BUFFER)
                if not data: break
                buffer += data.decode()

                while "\n" in buffer:
                    msg, buffer = buffer.split("\n", 1)
                    msg = msg.strip()
                    if not msg: continue

                    # התיקון: עדכון המשתנה username ממה שחוזר מהפונקציה
                    username = process_message(sock, username, msg)
            except Exception as e:
                break
    finally:
        with lock:
            if username and username in clients:
                cleanup_user(username)
                broadcast(f"[{now()}] {username} disconnected.\n")
        try:
            sock.close()
        except:
            pass


def start_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen()
    print(f"Server started on {HOST}:{PORT}")
    while True:
        c, _ = s.accept()
        threading.Thread(target=handle_client, args=(c,), daemon=True).start()


if __name__ == "__main__":
    start_server()