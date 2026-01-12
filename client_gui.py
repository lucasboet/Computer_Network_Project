import tkinter as tk
from tkinter import messagebox
import socket
import threading
import time

HOST = "127.0.0.1"
PORT = 9090
BUFFER = 1024

# GUI Styling configuration
COLOR_BG = "#36393f"
COLOR_SIDEBAR = "#2f3136"
COLOR_TEXT = "#dcddde"
COLOR_ACCENT = "#5865F2"
COLOR_INPUT_BG = "#40444b"
COLOR_ERROR = "#ed4245"
COLOR_SUCCESS = "#3ba55c"
COLOR_GOLD = "#f59e0b"
COLOR_CYAN = "#0ea5e9"
COLOR_PURPLE = "#8b5cf6"

FONT_MAIN = ("Segoe UI", 11)
FONT_BOLD = ("Segoe UI", 11, "bold")

# Initialize main window hidden
root = tk.Tk()
root.withdraw()
root.title("Chat Room")
root.geometry("1100x750")
root.configure(bg=COLOR_BG)

# Global variables
sock = None
running = True
last_ping = None
nickname = None


# ================= HELPER FUNCTIONS =================
def ask_custom_input(title, prompt, is_retry=False):
    # Create a modal dialog window
    dialog = tk.Toplevel(root)
    dialog.title(title)
    dialog.configure(bg=COLOR_BG)
    dialog.resizable(False, False)

    # Center the dialog on screen
    w, h = 400, 250
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - w) // 2
    y = (sh - h) // 2
    dialog.geometry(f"{w}x{h}+{x}+{y}")

    result = {"text": None}
    tk.Label(dialog, text=title, font=("Segoe UI", 16, "bold"), bg=COLOR_BG, fg="white").pack(pady=(20, 10))
    if is_retry:
        tk.Label(dialog, text="Username taken! Try another:", font=FONT_BOLD, bg=COLOR_BG, fg=COLOR_ERROR).pack(pady=5)
    else:
        tk.Label(dialog, text=prompt, font=FONT_MAIN, bg=COLOR_BG, fg="#b9bbbe").pack(pady=5)

    entry = tk.Entry(dialog, font=("Segoe UI", 14), bg=COLOR_INPUT_BG, fg="white", insertbackground="white",
                     relief=tk.FLAT, justify="center")
    entry.pack(pady=10, padx=40, fill=tk.X, ipady=5)
    entry.focus()

    def on_submit(event=None):
        val = entry.get().strip()
        if val:
            result["text"] = val
            dialog.destroy()

    entry.bind("<Return>", on_submit)
    tk.Button(dialog, text="Confirm", command=on_submit, bg=COLOR_ACCENT, fg="white", font=FONT_BOLD,
              relief=tk.FLAT).pack(pady=15, ipadx=20, ipady=5)
    dialog.grab_set()
    root.wait_window(dialog)
    return result["text"]


# ================= LOGIN =================
def perform_login():
    global sock, nickname
    try:
        # Connect to server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORT))
    except:
        messagebox.showerror("Error", "Server is offline.")
        root.destroy()
        exit()

    retry = False
    while True:
        # Ask for nickname
        name_prompt = ask_custom_input("Welcome", "Choose Nickname:", is_retry=retry)
        if not name_prompt:
            sock.close()
            root.destroy()
            exit()

        try:
            # Send nickname and check availability
            sock.sendall(name_prompt.encode())
            response = sock.recv(BUFFER).decode()
            if "TAKEN" in response:
                retry = True
            else:
                nickname = name_prompt
                break
        except:
            break


perform_login()
root.deiconify() # Show main window
root.title(f"Chat Room • {nickname}")


# ================= UI & LOGIC =================
def on_closing():
    global running
    running = False
    try:
        sock.send(b"/quit\n")
    except:
        pass
    try:
        sock.close()
    except:
        pass
    root.destroy()
    exit()


root.protocol("WM_DELETE_WINDOW", on_closing)


def send(cmd):
    # Helper to send data over socket
    if running and sock:
        try:
            sock.sendall((cmd + "\n").encode())
        except:
            pass


def do_ping():
    global last_ping
    last_ping = time.time()  # Start timer
    send("/ping")


# --- Layout ---
main_container = tk.Frame(root, bg=COLOR_BG)
main_container.pack(fill=tk.BOTH, expand=True)

# Sidebar setup
sidebar = tk.Frame(main_container, bg=COLOR_SIDEBAR, width=300)
sidebar.pack(side=tk.RIGHT, fill=tk.Y)
sidebar.pack_propagate(False)

# Members List
tk.Label(sidebar, text="MEMBERS", bg=COLOR_SIDEBAR, fg="#8e9297", font=("Segoe UI", 9, "bold")).pack(anchor="w",
                                                                                                     padx=15,
                                                                                                     pady=(15, 5))
users_list = tk.Listbox(sidebar, bg=COLOR_SIDEBAR, fg="#96989d", font=FONT_MAIN, bd=0, highlightthickness=0,
                        selectbackground=COLOR_INPUT_BG, selectforeground="white", height=8)
users_list.pack(fill=tk.X, padx=10)


def get_target():
    # Get selected user from listbox
    sel = users_list.curselection()
    if not sel:
        messagebox.showinfo("Info", "Select a user first.")
        return None
    val = users_list.get(sel[0])
    # Critical fix: remove '(Admin)' suffix but keep name
    if val.endswith(" (Admin)"):
        return val[:-8]
    return val


# Private Message
tk.Label(sidebar, text="PRIVATE MESSAGE", bg=COLOR_SIDEBAR, fg="#8e9297", font=("Segoe UI", 9, "bold")).pack(anchor="w",
                                                                                                             padx=15,
                                                                                                             pady=(15,
                                                                                                                   5))
pm_frame = tk.Frame(sidebar, bg=COLOR_SIDEBAR)
pm_frame.pack(fill=tk.X, padx=10)
pm_entry = tk.Entry(pm_frame, bg=COLOR_INPUT_BG, fg="white", font=("Segoe UI", 10), relief=tk.FLAT)
pm_entry.pack(fill=tk.X, pady=5, ipady=3)


def send_pm(event=None):
    target = get_target()
    msg = pm_entry.get().strip()
    if target and msg:
        send(f"@{target} {msg}")
        pm_entry.delete(0, tk.END)


pm_entry.bind("<Return>", send_pm)
tk.Button(pm_frame, text="Send PM", command=send_pm, bg=COLOR_GOLD, fg="white", font=FONT_BOLD, relief=tk.FLAT).pack(
    fill=tk.X)

# Actions Section
tk.Label(sidebar, text="ACTIONS", bg=COLOR_SIDEBAR, fg="#8e9297", font=("Segoe UI", 9, "bold")).pack(anchor="w",
                                                                                                     padx=15,
                                                                                                     pady=(15, 5))
btn_frame = tk.Frame(sidebar, bg=COLOR_SIDEBAR);
btn_frame.pack(fill=tk.X, padx=10)


def styled_btn(parent, text, cmd, color):
    # Helper to create styled buttons
    tk.Button(parent, text=text, command=cmd, bg=color, fg="white", font=("Segoe UI", 9, "bold"), relief=tk.FLAT).pack(
        fill=tk.X, pady=2)


def open_calc():
    # Open calculator popup
    cw = tk.Toplevel(root)
    cw.title("Calculator")
    cw.configure(bg=COLOR_BG)
    cw.geometry("300x200")

    f = tk.Frame(cw, bg=COLOR_BG)
    f.pack(pady=20)

    e1 = tk.Entry(f, width=8, bg=COLOR_INPUT_BG, fg="white", font=("Segoe UI", 16))
    e1.pack(side=tk.LEFT, padx=10)
    e2 = tk.Entry(f, width=8, bg=COLOR_INPUT_BG, fg="white", font=("Segoe UI", 16))
    e2.pack(side=tk.LEFT, padx=10)
    ops = tk.Frame(cw, bg=COLOR_BG)
    ops.pack(pady=20)

    def c(op): send(f"/calc {e1.get()} {op} {e2.get()}")

    for o in "+-*/": tk.Button(ops, text=o, width=5, height=2, command=lambda x=o: c(x),
                  bg=COLOR_ACCENT, fg="white", font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=5)


# Sidebar buttons
styled_btn(btn_frame, "Rename", lambda: send(f"/rename {ask_custom_input('Rename', 'New Name:')}"), COLOR_GOLD)
styled_btn(btn_frame, "Who Am I", lambda: send("/whoami"), "#3b82f6")
styled_btn(btn_frame, "Ping Server", do_ping, "#10b981")  # Fix: uses do_ping
styled_btn(btn_frame, "Uptime", lambda: send("/uptime"), COLOR_CYAN)
styled_btn(btn_frame, "Calculator", open_calc, COLOR_PURPLE)

# Admin Section
tk.Label(sidebar, text="ADMIN", bg=COLOR_SIDEBAR, fg="#8e9297", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=15,
                                                                                                   pady=(15, 5))
admin_box = tk.Frame(sidebar, bg=COLOR_SIDEBAR);
admin_box.pack(fill=tk.X, padx=10)
styled_btn(admin_box, "Check Admin", lambda: send("/admin"), COLOR_SIDEBAR)
styled_btn(admin_box, "Mute User", lambda: get_target() and send(f"/mute {get_target()}"), COLOR_ERROR)
styled_btn(admin_box, "Unmute User", lambda: get_target() and send(f"/unmute {get_target()}"), COLOR_SUCCESS)
styled_btn(admin_box, "Disconnect", on_closing, "#202225")

# Chat Layout
chat_layout = tk.Frame(main_container, bg=COLOR_BG)
chat_layout.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=20)
chat = tk.Text(chat_layout, bg=COLOR_BG, fg=COLOR_TEXT, font=("Segoe UI", 12), wrap=tk.WORD, bd=0, state=tk.DISABLED)
chat.pack(fill=tk.BOTH, expand=True)

# Configure text tags
chat.tag_config("server", foreground=COLOR_ACCENT, font=FONT_BOLD)
chat.tag_config("error", foreground=COLOR_ERROR)
chat.tag_config("pm", foreground=COLOR_GOLD, background="#33302a")
chat.tag_config("calc", foreground="#22d3ee", font=FONT_BOLD)

# Message Entry area
input_frame = tk.Frame(chat_layout, bg=COLOR_INPUT_BG, height=50)
input_frame.pack(fill=tk.X, pady=(15, 0));
input_frame.pack_propagate(False)
msg_entry = tk.Entry(input_frame, bg=COLOR_INPUT_BG, fg="white", font=FONT_MAIN, bd=0, insertbackground="white")
msg_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=15);
msg_entry.focus()


def send_msg(e=None):
    txt = msg_entry.get().strip()
    if txt: send(txt); msg_entry.delete(0, tk.END)


msg_entry.bind("<Return>", send_msg)
tk.Button(input_frame, text="SEND", command=send_msg, bg=COLOR_ACCENT, fg="white", font=FONT_BOLD, relief=tk.FLAT).pack(
    side=tk.RIGHT, fill=tk.Y, ipadx=20)


# Receiver
def receive_loop():
    global last_ping, running
    time.sleep(0.1);
    send("/users")
    buffer = ""
    while running:
        try:
            # Receive data
            data = sock.recv(BUFFER)
            if not data: break
            buffer += data.decode()
            # Handle buffer splitting
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                process_line(line.strip())
        except:
            break
    if running:
        # Show disconnect message
        chat.config(state=tk.NORMAL)
        chat.insert(tk.END, "\n[SYSTEM] Disconnected.\n", "error")
        chat.config(state=tk.DISABLED)


def process_line(msg):
    global last_ping
    if not msg: return
    tag = None

    # --- Ping Fix ---
    if msg == "Pong":
        if last_ping:
            rtt = int((time.time() - last_ping) * 1000)
            msg = f"Pong! 🏓 ({rtt} ms)"
            last_ping = None
        tag = "server"

    # Assign tags based on message content
    elif "[PM" in msg:
        tag = "pm"
    elif "[ERROR]" in msg:
        tag = "error"
    elif "[CALC]" in msg:
        tag = "calc"
    elif "Uptime" in msg:
        tag = "server"
    elif "Welcome" in msg:
        tag = "server"

    # Handle user list updates
    if msg.startswith("Connected users:"):
        users_list.delete(0, tk.END); return
    elif msg.startswith("- "):
        users_list.insert(tk.END, msg[2:]); return

    # Refresh user list on events
    if "joined" in msg or "disconnected" in msg or "changed name" in msg:
        send("/users")

    # Insert message into chat window
    chat.config(state=tk.NORMAL)
    chat.insert(tk.END, msg + "\n", tag)
    chat.see(tk.END)
    chat.config(state=tk.DISABLED)


# Start background listener thread
threading.Thread(target=receive_loop, daemon=True).start()
root.mainloop()