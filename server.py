import socket
import threading
import time
from datetime import datetime

HOST = "127.0.0.1"
PORT = 9090
BUFFER = 1024

clients = {}              # username -> socket
connection_order = []     # join order
muted_users = {}          # username -> mute_end_time or None
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


def send_help(sock):
    safe_send(
        sock,
        "\n[AVAILABLE COMMANDS]\n"
        "/users                - Show connected users\n"
        "/whoami               - Show your status\n"
        "/calc                 - to calculate a number by using: +, -, /, *\n"
        "/ping                 - Measure RTT\n"
        "/uptime               - Server uptime\n"
        "/rename <new_name>    - Change username\n"
        "/mute <user> [sec]    - Admin only\n"
        "/unmute <user>        - Admin only\n"
        "@username message     - Private message\n"
        "/admin                - Show admin\n"
        "/quit                 - Disconnect\n\n"
    )


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
        safe_send(
            clients[admin_username],
            f"[{now()}] You are now the administrator.\n"
        )
        broadcast(
            f"[{now()}] {admin_username} is now the administrator.\n"
        )
    else:
        admin_username = None


def cleanup_user(username):
    global admin_username

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
    if username not in muted_users:
        return False

    end = muted_users[username]
    if end is None:
        return True

    if time.time() < end:
        return True

    muted_users.pop(username)
    broadcast(f"[{now()}] {username} is no longer muted.\n")
    return False


def handle_client(sock):
    global admin_username
    username = None

    try:
        # ---- USERNAME REGISTRATION ----
        while True:
            safe_send(sock, "Enter username: ")
            username = sock.recv(BUFFER).decode().strip()

            if not username:
                continue

            with lock:
                if username in clients:
                    safe_send(sock, "Username taken, try again.\n")
                else:
                    clients[username] = sock
                    connection_order.append(username)
                    break

        with lock:
            if admin_username is None:
                admin_username = username
                safe_send(sock, f"[{now()}] You are the administrator.\n")

        safe_send(sock, f"[{now()}] Welcome {username}!\n")
        send_help(sock)
        broadcast(f"[{now()}] {username} joined the chat.\n")

        # ---- MAIN LOOP ----
        while True:
            data = sock.recv(BUFFER)
            if not data:
                break

            msg = data.decode().strip()

            if msg == "/quit":
                break

            # ---- BASIC COMMANDS ----
            if msg == "/ping":
                safe_send(sock, "Pong\n")
                continue

            if msg == "/uptime":
                uptime = int(time.time() - server_start_time)
                h, m, s = uptime // 3600, (uptime % 3600) // 60, uptime % 60
                safe_send(sock, f"Uptime: {h:02}:{m:02}:{s:02}\n")
                continue

            if msg == "/users":
                with lock:
                    users = "\n".join(
                        f"- {u}" + (" (Admin)" if u == admin_username else "")
                        for u in clients
                    )
                safe_send(sock, f"Connected users:\n{users}\n")
                continue

            if msg == "/admin":
                safe_send(sock, f"Admin: {admin_username}\n")
                continue

            if msg == "/whoami":
                role = "Administrator" if username == admin_username else "Regular user"
                muted = "Yes" if username in muted_users else "No"
                safe_send(sock, f"You are: {username}\nRole: {role}\nMuted: {muted}\n")
                continue

            # ---- RENAME ----
            if msg.startswith("/rename"):
                parts = msg.split(maxsplit=1)
                if len(parts) != 2:
                    safe_send(sock, "[ERROR] Usage: /rename <new_name>\n")
                    continue

                new_name = parts[1].strip()
                if not new_name:
                    continue

                with lock:
                    if new_name in clients:
                        safe_send(sock, "[ERROR] Username already taken.\n")
                        continue

                    clients[new_name] = clients.pop(username)
                    connection_order[connection_order.index(username)] = new_name

                    if username in muted_users:
                        muted_users[new_name] = muted_users.pop(username)

                    if username == admin_username:
                        admin_username = new_name

                    old = username
                    username = new_name

                broadcast(f" {old} changed username to {new_name}.\n")
                continue

            # ---- PRIVATE MESSAGE (ROBUST, SUPPORTS QUOTES) ----
            if msg.startswith("@"):
                msg = msg.strip()
                target = None
                text = None

                # Case 1: @"username with spaces" message
                if msg.startswith('@"'):
                    try:
                        end_quote = msg.find('"', 2)
                        if end_quote == -1:
                            raise ValueError

                        target = msg[2:end_quote].strip()
                        text = msg[end_quote + 1:].strip()

                        if not target or not text:
                            raise ValueError

                    except ValueError:
                        safe_send(
                            sock,
                            '[ERROR] Usage: @"username with spaces" message\n'
                        )
                        continue

                # Case 2: @username message
                else:
                    parts = msg.split(maxsplit=1)
                    if len(parts) != 2:
                        safe_send(sock, "[ERROR] Usage: @username message\n")
                        continue

                    target = parts[0][1:].strip()
                    text = parts[1].strip()

                with lock:
                    target_sock = clients.get(target)

                if target_sock is None:
                    safe_send(
                        sock,
                        f"[ERROR] User '{target}' not found.\n"
                    )
                    continue

                safe_send(
                    target_sock,
                    f"[{now()}] [PM from {username}] {text}\n"
                )
                continue

            # ---- MUTE / UNMUTE ----
            if msg.startswith("/mute"):
                if username != admin_username:
                    safe_send(sock, "[ERROR] Admin only.\n")
                    continue

                parts = msg.split()
                if len(parts) not in (2, 3):
                    safe_send(sock, "[ERROR] Usage: /mute <user> [seconds]\n")
                    continue

                target = parts[1]
                if target == admin_username or target not in clients:
                    continue

                if len(parts) == 2:
                    muted_users[target] = None
                    broadcast(f" {target} was muted permanently.\n")
                else:
                    try:
                        seconds = int(parts[2])
                        muted_users[target] = time.time() + seconds
                        broadcast(
                            f" {target} was muted for {seconds} seconds.\n"
                        )
                    except:
                        safe_send(sock, "[ERROR] Invalid time.\n")
                continue

            if msg.startswith("/unmute"):
                if username != admin_username:
                    safe_send(sock, "[ERROR] Admin only.\n")
                    continue

                parts = msg.split()
                if len(parts) != 2:
                    continue

                target = parts[1]
                muted_users.pop(target, None)
                broadcast(f" {target} was unmuted.\n")
                continue

            # ---- CALCULATOR (PRIVATE) ----
            if msg.startswith("/calc"):
                parts = msg.split()

                if len(parts) != 4:
                    safe_send(
                        sock,
                        "[ERROR] Usage: /calc <number> <operator> <number>\n"
                    )
                    continue

                try:
                    a = float(parts[1])
                    operator = parts[2]
                    b = float(parts[3])

                    if operator == "+":
                        result = a + b
                    elif operator == "-":
                        result = a - b
                    elif operator == "*":
                        result = a * b
                    elif operator == "/":
                        if b == 0:
                            safe_send(sock, "[ERROR] Division by zero\n")
                            continue
                        result = a / b
                    else:
                        safe_send(sock, "[ERROR] Invalid operator\n")
                        continue

                    safe_send(
                        sock,
                        f"[CALC] {a} {operator} {b} = {result}\n"
                    )

                except ValueError:
                    safe_send(sock, "[ERROR] Invalid numbers\n")

                continue

            # ---- BLOCK MUTED USER ----
            if is_muted(username):
                safe_send(sock, "You are muted.\n")
                continue

            # ---- NORMAL MESSAGE ----
            broadcast(f"[{now()}] {username}: {msg}\n")

    except Exception as e:
        print("ERROR:", e)
    finally:
        with lock:
            if username in clients:
                cleanup_user(username)
        broadcast(f" {username} disconnected.\n")


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
