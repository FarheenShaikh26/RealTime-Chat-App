import socket
import threading

SERVER = "127.0.0.1"  # agar server same computer me hai
PORT = 5000

def receive_messages(sock):
    while True:
        try:
            message = sock.recv(1024).decode()
            if message:
                print("\n" + message)
        except:
            print("Connection closed.")
            break

def send_messages(sock):
    while True:
        msg = input("")
        sock.send(msg.encode())

def start_client():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((SERVER, PORT))

    # 2 threads ban rahe hain: ek bhejne ke liye, ek receive karne ke liye
    thread1 = threading.Thread(target=receive_messages, args=(client,))
    thread2 = threading.Thread(target=send_messages, args=(client,))
    thread1.start()
    thread2.start()

start_client()