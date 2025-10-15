import socket
import threading

HOST = "0.0.0.0"   # server sab connections accept karega
PORT = 5000        # port number (same port client use karega)

clients = []  # sab connected clients ka record rakhega

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    conn.send("Enter your name: ".encode())
    name = conn.recv(1024).decode()
    welcome = f"{name} joined the chat!"
    print(welcome)
    
    # sab clients ko batana ki naya user aaya
    for client in clients:
        client.send(welcome.encode())
    
    clients.append(conn)

    # client ke messages receive karna
    while True:
        try:
            message = conn.recv(1024).decode()
            if not message:
                break
            full_message = f"{name}: {message}"
            print(full_message)

            # sab clients ko ye message bhejna
            for client in clients:
                if client != conn:
                    client.send(full_message.encode())
        except:
            break
    
    # agar user disconnect kare
    clients.remove(conn)
    conn.close()
    print(f"{name} left the chat.")
    for client in clients:
        client.send(f"{name} left the chat.".encode())

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"Server started on {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()

start_server()