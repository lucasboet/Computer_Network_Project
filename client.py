import socket
import threading
import time

HOST = "127.0.0.1"
PORT = 9090
BUFFER = 1024

running = True
last_ping = None


def listen(sock):
    global running, last_ping
    try:
        while running:
            data = sock.recv(BUFFER)
            if not data:
                print("\n[Disconnected]")
                running = False
                break

            text = data.decode().strip()

            if text == "Pong" and last_ping:
                rtt = int((time.time() - last_ping) * 1000)
                print(f"\nPong! RTT = {rtt} ms")
                last_ping = None
            else:
                print("\r" + text)

            print("> ", end="", flush=True)
    except:
        running = False


def start_client():
    global running, last_ping
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))

    threading.Thread(target=listen, args=(sock,), daemon=True).start()

    try:
        while running:
            msg = input("> ")

            if msg == "/ping":
                last_ping = time.time()

            sock.sendall((msg + "\n").encode())

            if msg == "/quit":
                running = False
                break
    finally:
        sock.close()
        print("Client closed.")


if __name__ == "__main__":
    start_client()
