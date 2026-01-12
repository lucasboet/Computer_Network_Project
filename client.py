import socket
import threading
import time

# Server connection details
HOST = "127.0.0.1"
PORT = 9090
BUFFER = 1024

# Global state flags
running = True
last_ping = None


def listen(sock):
    global running, last_ping
    try:
        while running:
            # Receive data from server
            data = sock.recv(BUFFER)
            if not data:
                # Server closed connection
                print("\n[Disconnected]")
                running = False
                break

            # Decode message
            text = data.decode().strip()

            # Handle ping response
            if text == "Pong" and last_ping:
                rtt = int((time.time() - last_ping) * 1000)
                print(f"\nPong! RTT = {rtt} ms")
                last_ping = None
            else:
                # Print normal message
                print("\r" + text)

            # Reprint input prompt
            print("> ", end="", flush=True)
    except:
        running = False


def start_client():
    global running, last_ping
    # Create TCP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))

    # Start listener thread
    threading.Thread(target=listen, args=(sock,), daemon=True).start()

    try:
        while running:
            # Get user input
            msg = input("> ")

            # Track ping time
            if msg == "/ping":
                last_ping = time.time()

            # Send message to server
            sock.sendall((msg + "\n").encode())

            # Handle quit command
            if msg == "/quit":
                running = False
                break
    finally:
        # Cleanup connection
        sock.close()
        print("Client closed.")


if __name__ == "__main__":
    start_client()