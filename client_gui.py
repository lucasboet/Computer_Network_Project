import tkinter as tk
from tkinter import messagebox
import socket
import threading
import time

# ================= CONFIG & COLORS =================
HOST = "127.0.0.1"
PORT = 9090
BUFFER = 1024

# עיצוב Dark Mode מלא
COLOR_BG = "#36393f"
COLOR_SIDEBAR = "#2f3136"
COLOR_TEXT = "#dcddde"
COLOR_ACCENT = "#5865F2"
COLOR_ACCENT_HOVER = "#4752c4"
COLOR_INPUT_BG = "#40444b"
COLOR_ERROR = "#ed4245"
COLOR_SUCCESS = "#3ba55c"
COLOR_GOLD = "#f59e0b"

FONT_MAIN = ("Segoe UI", 11)
FONT_BOLD = ("Segoe UI", 11, "bold")

# יצירת ה-Root מראש והסתרתו (מונע קריסות)
root = tk.Tk()
root.withdraw()
root.title("Chat Room")
root.geometry("1100x750")
root.configure(bg=COLOR_BG)

sock = None
running = True
last_ping = None
nickname = None


# ================= CUSTOM DIALOGS =================
def ask_custom_input(title, prompt):
    """ חלונית קלט מעוצבת שחורה במקום החלונית הלבנה הישנה """
    dialog = tk.Toplevel(root)
    dialog.title(title)
    dialog.configure(bg=COLOR_BG)
    dialog.resizable(False, False)

    # מרכוז החלונית
    w, h = 400, 220
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - w) // 2
    y = (sh - h) // 2
    dialog.geometry(f"{w}x{h}+{x}+{y}")

    result = {"text": None}

    tk.Label(dialog, text=title, font=("Segoe UI", 16, "bold"), bg=COLOR_BG, fg="white").pack(pady=(25, 10))
    tk.Label(dialog, text=prompt, font=FONT_MAIN, bg=COLOR_BG, fg="#b9bbbe").pack(pady=5)

    entry = tk.Entry(
        dialog, font=("Segoe UI", 14), bg=COLOR_INPUT_BG, fg="white",
        insertbackground="white", relief=tk.FLAT, justify="center"
    )
    entry.pack(pady=10, padx=40, fill=tk.X, ipady=5)
    entry.focus()

    def on_submit(event=None):
        val = entry.get().strip()
        if val:
            result["text"] = val
            dialog.destroy()

    entry.bind("<Return>", on_submit)

    btn = tk.Button(
        dialog, text="Confirm", command=on_submit,
        bg=COLOR_ACCENT, fg="white", font=FONT_BOLD, relief=tk.FLAT,
        activebackground=COLOR_ACCENT_HOVER, activeforeground="white"
    )
    btn.pack(pady=15, ipadx=20, ipady=5)

    dialog.grab_set()
    root.wait_window(dialog)
    return result["text"]


# ================= LOGIN PROCESS =================
# 1. פתיחת החלונית המעוצבת לבחירת שם
nickname = ask_custom_input("Welcome", "Choose your display name:")

if not nickname:
    root.destroy()
    exit()

# 2. ניסיון התחברות
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)  # טיימאאוט קצר למקרה שהשרת כבוי
    sock.connect((HOST, PORT))
    sock.settimeout(None)
except Exception as e:
    messagebox.showerror("Connection Error",
                         f"Cannot connect to server.\nMake sure 'server.py' is running!\n\nError: {e}")
    root.destroy()
    exit()

# 3. הצגת החלון הראשי
root.deiconify()
root.title(f"Chat Room • {nickname}")


# ================= UI BUILDER =================
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
    if running and sock:
        try:
            sock.sendall((cmd + "\n").encode())
        except:
            pass


# --- Main Layout ---
main_container = tk.Frame(root, bg=COLOR_BG)
main_container.pack(fill=tk.BOTH, expand=True)

# --- Sidebar ---
sidebar = tk.Frame(main_container, bg=COLOR_SIDEBAR, width=280)
sidebar.pack(side=tk.RIGHT, fill=tk.Y)
sidebar.pack_propagate(False)

tk.Label(sidebar, text="MEMBERS", bg=COLOR_SIDEBAR, fg="#8e9297", font=("Segoe UI", 9, "bold")).pack(anchor="w",
                                                                                                     padx=15,
                                                                                                     pady=(20, 10))
users_list = tk.Listbox(
    sidebar, bg=COLOR_SIDEBAR, fg="#96989d", font=FONT_MAIN,
    bd=0, highlightthickness=0, selectbackground=COLOR_INPUT_BG, selectforeground="white",
    activestyle="none", height=15
)
users_list.pack(fill=tk.X, padx=10)


def get_target():
    sel = users_list.curselection()
    if not sel:
        messagebox.showinfo("Select User", "Please select a user from the list first.")
        return None
    return users_list.get(sel[0]).split(" ")[0]


# --- Buttons ---
tk.Label(sidebar, text="ACTIONS", bg=COLOR_SIDEBAR, fg="#8e9297", font=("Segoe UI", 9, "bold")).pack(anchor="w",
                                                                                                     padx=15,
                                                                                                     pady=(20, 5))
btn_frame = tk.Frame(sidebar, bg=COLOR_SIDEBAR)
btn_frame.pack(fill=tk.X, padx=10)


def styled_btn(parent, text, cmd, color=COLOR_ACCENT):
    tk.Button(
        parent, text=text, command=cmd,
        bg=color, fg="white", activebackground=color, activeforeground="white",
        font=("Segoe UI", 10, "bold"), relief=tk.FLAT, bd=0, cursor="hand2"
    ).pack(fill=tk.X, pady=3, ipady=3)


def do_rename():
    # משתמשים באותה חלונית מעוצבת גם לשינוי שם!
    new = ask_custom_input("Change Name", "Enter new nickname:")
    if new: send(f"/rename {new}")


def open_calc():
    cw = tk.Toplevel(root)
    cw.title("Calc")
    cw.geometry("300x250")
    cw.configure(bg=COLOR_BG)
    tk.Label(cw, text="Calculator", font=("Segoe UI", 14, "bold"), bg=COLOR_BG, fg="white").pack(pady=15)
    f = tk.Frame(cw, bg=COLOR_BG);
    f.pack()
    e1 = tk.Entry(f, width=8, bg=COLOR_INPUT_BG, fg="white", font=FONT_MAIN, relief=tk.FLAT, justify="center");
    e1.pack(side=tk.LEFT, padx=5, ipady=3)
    e2 = tk.Entry(f, width=8, bg=COLOR_INPUT_BG, fg="white", font=FONT_MAIN, relief=tk.FLAT, justify="center");
    e2.pack(side=tk.LEFT, padx=5, ipady=3)

    def c(op):
        try:
            send(f"/calc {float(e1.get())} {op} {float(e2.get())}")
        except:
            pass

    ops = tk.Frame(cw, bg=COLOR_BG);
    ops.pack(pady=20)
    for o in "+-*/": tk.Button(ops, text=o, width=4, command=lambda x=o: c(x), bg=COLOR_SIDEBAR, fg="white",
                               relief=tk.FLAT).pack(side=tk.LEFT, padx=3)


styled_btn(btn_frame, "Rename", do_rename, COLOR_GOLD)
styled_btn(btn_frame, "Who Am I", lambda: send("/whoami"), "#3b82f6")
styled_btn(btn_frame, "Ping Server", lambda: (send("/ping"), globals().update(last_ping=time.time())), "#10b981")
styled_btn(btn_frame, "Calculator", open_calc, "#6366f1")

tk.Label(sidebar, text="ADMIN", bg=COLOR_SIDEBAR, fg="#8e9297", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=15,
                                                                                                   pady=(20, 5))
admin_box = tk.Frame(sidebar, bg=COLOR_SIDEBAR);
admin_box.pack(fill=tk.X, padx=10)
styled_btn(admin_box, "Check Admin", lambda: send("/admin"), COLOR_SIDEBAR)
styled_btn(admin_box, "Mute User", lambda: get_target() and send(f"/mute {get_target()}"), COLOR_ERROR)
styled_btn(admin_box, "Unmute User", lambda: get_target() and send(f"/unmute {get_target()}"), COLOR_SUCCESS)
styled_btn(admin_box, "Disconnect", on_closing, "#202225")

# --- Chat Area ---
chat_layout = tk.Frame(main_container, bg=COLOR_BG)
chat_layout.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=20)
chat = tk.Text(chat_layout, bg=COLOR_BG, fg=COLOR_TEXT, font=("Segoe UI", 12), wrap=tk.WORD, bd=0, highlightthickness=0,
               state=tk.DISABLED, padx=10, pady=10)
chat.pack(fill=tk.BOTH, expand=True)
chat.tag_config("server", foreground=COLOR_ACCENT, font=FONT_BOLD)
chat.tag_config("error", foreground=COLOR_ERROR)
chat.tag_config("pm", foreground=COLOR_GOLD, background="#33302a")
chat.tag_config("admin", foreground=COLOR_SUCCESS)

input_frame = tk.Frame(chat_layout, bg=COLOR_INPUT_BG, height=50)
input_frame.pack(fill=tk.X, pady=(15, 0));
input_frame.pack_propagate(False)
msg_entry = tk.Entry(input_frame, bg=COLOR_INPUT_BG, fg="white", font=FONT_MAIN, bd=0, highlightthickness=0,
                     insertbackground="white")
msg_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=15);
msg_entry.focus()


def send_msg(e=None):
    txt = msg_entry.get().strip()
    if txt: send(txt); msg_entry.delete(0, tk.END)


msg_entry.bind("<Return>", send_msg)
tk.Button(input_frame, text="SEND", command=send_msg, bg=COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"), bd=0,
          relief=tk.FLAT).pack(side=tk.RIGHT, fill=tk.Y, ipadx=20)


# ================= NETWORK LOGIC =================
def receive_loop():
    global last_ping, running
    time.sleep(0.1);
    send(nickname);
    time.sleep(0.1);
    send("/users")  # Login Handshake
    buffer = ""
    while running:
        try:
            data = sock.recv(BUFFER)
            if not data: break
            buffer += data.decode()
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                process_line(line.strip())
        except:
            break
    if running:
        chat.config(state=tk.NORMAL)
        chat.insert(tk.END, "\n[SYSTEM] Disconnected from server.\n", "error")
        chat.config(state=tk.DISABLED)


def process_line(msg):
    global last_ping
    if not msg: return
    tag = None
    if msg == "Pong" and last_ping:
        msg = f"Pong! 🏓 ({int((time.time() - last_ping) * 1000)} ms)";
        tag = "server";
        last_ping = None
    elif "[PM from" in msg:
        tag = "pm"
    elif "[ERROR]" in msg:
        tag = "error"
    elif "administrator" in msg.lower():
        tag = "admin"
    elif "Welcome" in msg:
        tag = "server"

    if msg.startswith("Connected users:"):
        users_list.delete(0, tk.END); return
    elif msg.startswith("- "):
        users_list.insert(tk.END, msg[2:]); return

    if "joined the chat" in msg:
        u = msg.split("] ")[1].split(" ")[0]
        if u not in users_list.get(0, tk.END): users_list.insert(tk.END, u)
    elif "disconnected" in msg or "changed name to" in msg:
        send("/users")

    chat.config(state=tk.NORMAL)
    chat.insert(tk.END, msg + "\n", tag)
    chat.see(tk.END)
    chat.config(state=tk.DISABLED)


threading.Thread(target=receive_loop, daemon=True).start()
root.mainloop()