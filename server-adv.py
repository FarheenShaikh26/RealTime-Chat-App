import socket
import threading
import json
import sqlite3
import hashlib
import base64
import os
from datetime import datetime
from cryptography.fernet import Fernet

class ChatServer:
    def init(self, host='127.0.0.1', port=5555):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = {}  # {username: (socket, current_room)}
        self.rooms = {'general': [], 'random': [], 'tech': []}
        self.encryption_key = Fernet.generate_key()
        self.cipher = Fernet(self.encryption_key)
        self.init_database()
        
    def init_database(self):
        """Initialize SQLite database for users and messages"""
        self.conn = sqlite3.connect('chat_data.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        # Users table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Messages table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room TEXT NOT NULL,
                username TEXT NOT NULL,
                message TEXT NOT NULL,
                message_type TEXT DEFAULT 'text',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def hash_password(self, password):
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def register_user(self, username, password):
        """Register a new user"""
        try:
            hashed_pw = self.hash_password(password)
            self.cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                              (username, hashed_pw))
            self.conn.commit()
            return True, "Registration successful"
        except sqlite3.IntegrityError:
            return False, "Username already exists"
        except Exception as e:
            return False, f"Registration failed: {str(e)}"
    
    def authenticate_user(self, username, password):
        """Authenticate user credentials"""
        hashed_pw = self.hash_password(password)
        self.cursor.execute('SELECT * FROM users WHERE username=? AND password=?',
                          (username, hashed_pw))
        return self.cursor.fetchone() is not None
    
    def save_message(self, room, username, message, msg_type='text'):
        """Save message to database"""
        self.cursor.execute(
            'INSERT INTO messages (room, username, message, message_type) VALUES (?, ?, ?, ?)',
            (room, username, message, msg_type)
        )
        self.conn.commit()
    
    def get_message_history(self, room, limit=50):
        """Retrieve message history for a room"""
        self.cursor.execute(
            'SELECT username, message, message_type, timestamp FROM messages WHERE room=? ORDER BY timestamp DESC LIMIT ?',
            (room, limit)
        )
        messages = self.cursor.fetchall()
        return list(reversed(messages))
    
    def encrypt_message(self, message):
        """Encrypt message"""
        return base64.b64encode(self.cipher.encrypt(message.encode())).decode()
    
    def decrypt_message(self, encrypted_message):
        """Decrypt message"""
        try:
            return self.cipher.decrypt(base64.b64decode(encrypted_message)).decode()
        except:
            return encrypted_message
    
    def broadcast_to_room(self, room, message, exclude_user=None):
        """Broadcast message to all users in a room"""
        if room in self.rooms:
            for username in self.rooms[room]:
                if username != exclude_user and username in self.clients:
                    try:
                        client_socket = self.clients[username][0]
                        client_socket.send(message.encode())
                    except:
                        self.remove_client(username)
    
    def remove_client(self, username):
        """Remove client from server"""
        if username in self.clients:
            current_room = self.clients[username][1]
            if current_room and current_room in self.rooms:
                if username in self.rooms[current_room]:
                    self.rooms[current_room].remove(username)
            del self.clients[username]
    
    def handle_client(self, client_socket, address):
        """Handle individual client connection"""
        username = None
        current_room = None
        
        try:
            # Send encryption key
            client_socket.send(json.dumps({
                'type': 'encryption_key',
                'key': base64.b64encode(self.encryption_key).decode()
            }).encode())
            
            # Authentication loop
            authenticated = False
            while not authenticated:
                auth_data = client_socket.recv(4096).decode()
                auth_msg = json.loads(auth_data)
                
                if auth_msg['type'] == 'register':
                    success, message = self.register_user(auth_msg['username'], auth_msg['password'])
                    client_socket.send(json.dumps({
                        'type': 'auth_response',
                        'success': success,
                        'message': message
                    }).encode())
                    
                elif auth_msg['type'] == 'login':
                    if self.authenticate_user(auth_msg['username'], auth_msg['password']):
                        if auth_msg['username'] in self.clients:
                            client_socket.send(json.dumps({
                                'type': 'auth_response',
                                'success': False,
                                'message': 'User already logged in'
                            }).encode())
                        else:
                            username = auth_msg['username']
                            self.clients[username] = (client_socket, None)
                            authenticated = True
                            
                            # Send available rooms
                            client_socket.send(json.dumps({
                                'type': 'auth_response',
                                'success': True,
                                'message': 'Login successful',
                                'rooms': list(self.rooms.keys())
                            }).encode())
                    else:
                        client_socket.send(json.dumps({
                            'type': 'auth_response',
                            'success': False,
                            'message': 'Invalid credentials'
                        }).encode())
            
            # Main message loop
            while True:
                data = client_socket.recv(4096).decode()
                if not data:
                    break
                
                message = json.loads(data)
                
                if message['type'] == 'join_room':
                    room = message['room']
                    
                    # Leave current room
                    if current_room and current_room in self.rooms:
                        if username in self.rooms[current_room]:
                            self.rooms[current_room].remove(username)
                        self.broadcast_to_room(current_room, json.dumps({
                            'type': 'user_left',
                            'username': username,
                            'room': current_room
                        }))
                    
                    # Join new room
                    if room not in self.rooms:
                        self.rooms[room] = []
                    self.rooms[room].append(username)
                    current_room = room
                    self.clients[username] = (client_socket, current_room)
                    
                    # Send message history
                    history = self.get_message_history(room)
                    client_socket.send(json.dumps({
                        'type': 'message_history',
                        'history': history,
                        'room': room
                    }).encode())
                    
                    # Notify room
                    self.broadcast_to_room(room, json.dumps({
                        'type': 'user_joined',
                        'username': username,
                        'room': room,
                        'users': self.rooms[room]
                    }), exclude_user=username)
                    
                elif message['type'] == 'text_message':
                    if current_room:
                        decrypted = self.decrypt_message(message['content'])
                        self.save_message(current_room, username, decrypted)
                        
                        self.broadcast_to_room(current_room, json.dumps({
                            'type': 'text_message',
                            'username': username,
                            'content': message['content'],
                            'timestamp': datetime.now().strftime('%H:%M:%S')
                        }))
                
                elif message['type'] == 'multimedia':
                    if current_room:
                        self.save_message(current_room, username, 
                                        f"[{message['media_type']}]", 
                                        message['media_type'])
                        
                        self.broadcast_to_room(current_room, json.dumps({
                            'type': 'multimedia',
                            'username': username,
                            'media_type': message['media_type'],
                            'data': message['data'],
                            'filename': message.get('filename', 'file'),
                            'timestamp': datetime.now().strftime('%H:%M:%S')
                        }))
                
                elif message['type'] == 'emoji':
                    if current_room:
                        self.broadcast_to_room(current_room, json.dumps({
                            'type': 'emoji',
                            'username': username,
                            'emoji': message['emoji'],
                            'timestamp': datetime.now().strftime('%H:%M:%S')
                        }))
        
        except Exception as e:
            print(f"Error handling client {username}: {e}")
        finally:
            if username:
                self.remove_client(username)
                if current_room:
                    self.broadcast_to_room(current_room, json.dumps({
                        'type': 'user_left',
                        'username': username,
                        'room': current_room
                    }))
            client_socket.close()
            print(f"Connection closed: {address}")
    
    def start(self):
        """Start the server"""
        self.server.bind((self.host, self.port))
        self.server.listen()
        print(f"Server started on {self.host}:{self.port}")
        print("Waiting for connections...")
        
        try:
            while True:
                client_socket, address = self.server.accept()
                print(f"New connection from {address}")
                thread = threading.Thread(target=self.handle_client, 
                                        args=(client_socket, address))
                thread.daemon = True
                thread.start()
        except KeyboardInterrupt:
            print("\nServer shutting down...")
        finally:
            self.server.close()
            self.conn.close()

if __name__== 'main':
    server = ChatServer()
    server.start()