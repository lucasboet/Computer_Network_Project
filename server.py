import socket
import threading
import time
from datetime import datetime

# Server configuration
HOST = "127.0.0.1"
PORT = 9090
BUFFER = 1024

# Global state management
clients = {}
connection_order = []
muted_users = {}
admin_username = None
server_start_time = time.time()

# Lock for thread safety
lock = threading.Lock()


def now():
    # Return current time as a string
    return datetime.now().strftime("%H:%M:%S")


def safe_send(sock, msg):
    # Try to send a message to a socket
    try:
        sock.sendall(msg.encode())
        return True
    except:
        return False


# --- Critical fix logic ---
def broadcast(msg):
    # Copy client list safely while holding the lock
    # Prevents server crash if a user disconnects suddenly
    with lock:
        active_clients = list(clients.items())

    dead = []
    # Iterate over copied list to send messages
    for u, s in active_clients:
        if not safe_send(s, msg):
            dead.append(u)

    # Clean up disconnected users
    for u in dead:
        cleanup_user(u)


# -----------------------------

def promote_new_admin():
    global admin_username
    # Check if there are other users to promote
    if connection_order:
        admin_username = connection_order[0]
        # Verify user existence before sending
        if admin_username in clients:
            safe_send(clients[admin_username], f"[{now()}] You are now the administrator.\n")
        broadcast(f"[{now()}] {admin_username} is now the administrator.\n")
    else:
        admin_username = None


def cleanup_user(username):
    global admin_username

    # Use lock to prevent race conditions during deletion
    with lock:
        if username not in clients: return
        sock = clients.pop(username, None)
        if username in muted_users: muted_users.pop(username, None)
        if username in connection_order: connection_order.remove(username)

    # Close the socket if it exists
    if sock:
        try:
            sock.close()
        except:
            pass

    # Promote new admin if the current one left
    if username == admin_username:
        promote_new_admin()


def process_message(sock, current_username, msg):
    global admin_username

    # Handle quit command
    if msg == "/quit":
        safe_send(sock, "[SERVER] You disconnected.\n")
        raise Exception("Quit")

    # Handle ping command
    if msg == "/ping":
        safe_send(sock, "Pong\n")
        return current_username

    # Handle uptime command
    if msg == "/uptime":
        seconds = int(time.time() - server_start_time)
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        safe_send(sock, f"[SERVER] Server Uptime: {h:02d}:{m:02d}:{s:02d}\n")
        return current_username

    # Handle users list command
    if msg == "/users":
        with lock:  # Lock briefly to read the list
            users = list(clients.keys())
            admin = admin_username
        text = "\n".join(f"- {u}" + (" (Admin)" if u == admin else "") for u in users)
        safe_send(sock, f"Connected users:\n{text}\n")
        return current_username

    # Handle admin status command
    if msg == "/admin":
        safe_send(sock, f"Admin: {admin_username}\n")
        return current_username

    # Handle whoami command
    if msg == "/whoami":
        role = "Administrator" if current_username == admin_username else "Regular user"
        safe_send(sock, f"You are: {current_username}\nRole: {role}\n")
        return current_username

    # Handle rename command
    if msg.startswith("/rename"):
        parts = msg.split(maxsplit=1)
        if len(parts) != 2: return current_username
        new_name = parts[1].strip()

        with lock:
            if new_name in clients:
                safe_send(sock, f"[ERROR] The name '{new_name}' is already taken.\n")
                return current_username

            # Update client dictionary and lists
            clients[new_name] = clients.pop(current_username)
            if current_username in connection_order:
                connection_order[connection_order.index(current_username)] = new_name
            if current_username == admin_username:
                admin_username = new_name

            old_name = current_username
            current_username = new_name

        broadcast(f"[{now()}] {old_name} changed name to {new_name}.\n")
        return current_username

    # Handle private messages
    if msg.startswith("@"):
        try:
            target_name, text = msg[1:].split(" ", 1)

            # Safely retrieve target socket
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

    # Handle calculator command
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

    # Handle mute/unmute commands
    if msg.startswith("/mute") or msg.startswith("/unmute"):
        if current_username != admin_username:
            safe_send(sock, "[ERROR] Admin only.\n")
            return current_username

        parts = msg.split(maxsplit=1)
        if len(parts) < 2: return current_username
        target = parts[1]

        if msg.startswith("/mute"):
            # Check if user exists using lock
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

    # Check if user is muted
    if current_username in muted_users:
        safe_send(sock, "[SYSTEM] You are muted.\n")
        return current_username

    # Broadcast standard message
    broadcast(f"[{now()}] {current_username}: {msg}\n")
    return current_username


def handle_client(sock):
    global admin_username
    username = None
    buffer = ""

    try:
        while True:
            # Receive initial data
            data = sock.recv(BUFFER)
            if not data: return
            temp_name = data.decode().strip()

            # Check if name is available
            with lock:
                if temp_name in clients:
                    safe_send(sock, "TAKEN")
                else:
                    safe_send(sock, "OK")
                    username = temp_name
                    clients[username] = sock
                    connection_order.append(username)
                    # Break loop if successful
                    break

        # Assign admin role if needed
        with lock:
            if admin_username is None:
                admin_username = username
                safe_send(sock, f"[{now()}] You are the administrator.\n")

        safe_send(sock, f"[{now()}] Welcome {username}!\n")
        broadcast(f"[{now()}] {username} joined the chat.\n")

        # Main message loop
        while True:
            data = sock.recv(BUFFER)
            if not data: break
            buffer += data.decode()

            # Handle TCP buffering and line splitting
            while "\n" in buffer:
                msg, buffer = buffer.split("\n", 1)
                msg = msg.strip()
                if not msg: continue
                username = process_message(sock, username, msg)

    except:
        pass
    finally:
        # Cleanup logic on exit
        if username:
            cleanup_user(username)
            # Broadcast disconnect only if user was logged in
            broadcast(f"[{now()}] {username} disconnected.\n")
        else:
            try:
                sock.close()
            except:
                pass


def start_server():
    # Initialize server socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Allow immediate port reuse after stop
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen()
    print(f"Server started on {HOST}:{PORT}")
    # Accept incoming connections
    while True:
        c, _ = s.accept()
        threading.Thread(target=handle_client, args=(c,), daemon=True).start()


if __name__ == "__main__":
    start_server()