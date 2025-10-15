import socket
import threading
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import base64
from datetime import datetime
from cryptography.fernet import Fernet
from PIL import Image, ImageTk
import io
import os

class ChatClient:
    def _init_(self, root):
        self.root = root
        self.root.title("Advanced Chat Application")
        self.root.geometry("1000x700")
        self.root.configure(bg="#1e1e1e")
        
        self.socket = None
        self.username = None
        self.current_room = None
        self.cipher = None
        self.running = False
        
        # Emoji list
        self.emojis = ['😀', '😂', '😍', '🤔', '👍', '❤', '🎉', '🔥', '💯', '✨', 
                      '😎', '🙌', '👏', '💪', '🎯', '🚀', '⭐', '💡', '📱', '💻']
        
        # Style configuration
        self.bg_color = "#1e1e1e"
        self.fg_color = "#ffffff"
        self.accent_color = "#0d7377"
        self.secondary_color = "#14a085"
        self.input_bg = "#2d2d2d"
        
        self.show_login_screen()
    
    def show_login_screen(self):
        """Display login/registration screen"""
        self.login_frame = tk.Frame(self.root, bg=self.bg_color)
        self.login_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title = tk.Label(self.login_frame, text="💬 Advanced Chat", 
                        font=("Arial", 32, "bold"),
                        bg=self.bg_color, fg=self.accent_color)
        title.pack(pady=50)
        
        # Login container
        container = tk.Frame(self.login_frame, bg=self.input_bg, padx=40, pady=40)
        container.pack()
        
        # Server connection
        tk.Label(container, text="Server:", font=("Arial", 12), 
                bg=self.input_bg, fg=self.fg_color).grid(row=0, column=0, sticky="w", pady=5)
        self.server_entry = tk.Entry(container, font=("Arial", 12), width=30)
        self.server_entry.insert(0, "127.0.0.1")
        self.server_entry.grid(row=0, column=1, pady=5, padx=10)
        
        tk.Label(container, text="Port:", font=("Arial", 12), 
                bg=self.input_bg, fg=self.fg_color).grid(row=1, column=0, sticky="w", pady=5)
        self.port_entry = tk.Entry(container, font=("Arial", 12), width=30)
        self.port_entry.insert(0, "5555")
        self.port_entry.grid(row=1, column=1, pady=5, padx=10)
        
        # Username
        tk.Label(container, text="Username:", font=("Arial", 12), 
                bg=self.input_bg, fg=self.fg_color).grid(row=2, column=0, sticky="w", pady=5)
        self.username_entry = tk.Entry(container, font=("Arial", 12), width=30)
        self.username_entry.grid(row=2, column=1, pady=5, padx=10)
        
        # Password
        tk.Label(container, text="Password:", font=("Arial", 12), 
                bg=self.input_bg, fg=self.fg_color).grid(row=3, column=0, sticky="w", pady=5)
        self.password_entry = tk.Entry(container, font=("Arial", 12), width=30, show="*")
        self.password_entry.grid(row=3, column=1, pady=5, padx=10)
        self.password_entry.bind('<Return>', lambda e: self.login())
        
        # Buttons
        btn_frame = tk.Frame(container, bg=self.input_bg)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        login_btn = tk.Button(btn_frame, text="Login", font=("Arial", 12, "bold"),
                             bg=self.accent_color, fg="white", width=12,
                             command=self.login, cursor="hand2")
        login_btn.pack(side=tk.LEFT, padx=5)
        
        register_btn = tk.Button(btn_frame, text="Register", font=("Arial", 12, "bold"),
                                bg=self.secondary_color, fg="white", width=12,
                                command=self.register, cursor="hand2")
        register_btn.pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_label = tk.Label(self.login_frame, text="", font=("Arial", 10),
                                     bg=self.bg_color, fg="#ff6b6b")
        self.status_label.pack(pady=10)
    
    def connect_to_server(self):
        """Connect to chat server"""
        try:
            host = self.server_entry.get()
            port = int(self.port_entry.get())
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            
            # Receive encryption key
            key_data = json.loads(self.socket.recv(4096).decode())
            if key_data['type'] == 'encryption_key':
                key = base64.b64decode(key_data['key'])
                self.cipher = Fernet(key)
            
            return True
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")
            return False
    
    def login(self):
        """Login to the chat"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            self.status_label.config(text="Please enter username and password")
            return
        
        if self.connect_to_server():
            try:
                # Send login request
                self.socket.send(json.dumps({
                    'type': 'login',
                    'username': username,
                    'password': password
                }).encode())
                
                # Wait for response
                response = json.loads(self.socket.recv(4096).decode())
                
                if response['success']:
                    self.username = username
                    self.rooms = response['rooms']
                    self.show_chat_screen()
                    
                    # Start receiving messages
                    self.running = True
                    recv_thread = threading.Thread(target=self.receive_messages)
                    recv_thread.daemon = True
                    recv_thread.start()
                else:
                    self.status_label.config(text=response['message'])
                    self.socket.close()
            except Exception as e:
                self.status_label.config(text=f"Login failed: {str(e)}")
                self.socket.close()
    
    def register(self):
        """Register new account"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            self.status_label.config(text="Please enter username and password")
            return
        
        if len(password) < 4:
            self.status_label.config(text="Password must be at least 4 characters")
            return
        
        if self.connect_to_server():
            try:
                # Send registration request
                self.socket.send(json.dumps({
                    'type': 'register',
                    'username': username,
                    'password': password
                }).encode())
                
                # Wait for response
                response = json.loads(self.socket.recv(4096).decode())
                
                if response['success']:
                    self.status_label.config(text=response['message'], fg="#4ecdc4")
                    messagebox.showinfo("Success", "Registration successful! Please login.")
                else:
                    self.status_label.config(text=response['message'], fg="#ff6b6b")
                
                self.socket.close()
            except Exception as e:
                self.status_label.config(text=f"Registration failed: {str(e)}")
                self.socket.close()
    
    def show_chat_screen(self):
        """Display main chat interface"""
        self.login_frame.destroy()
        
        # Main container
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left sidebar - Rooms
        sidebar = tk.Frame(main_frame, bg=self.input_bg, width=200)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        sidebar.pack_propagate(False)
        
        tk.Label(sidebar, text="Chat Rooms", font=("Arial", 14, "bold"),
                bg=self.input_bg, fg=self.accent_color).pack(pady=10)
        
        # Room list
        self.room_listbox = tk.Listbox(sidebar, font=("Arial", 11),
                                       bg=self.input_bg, fg=self.fg_color,
                                       selectbackground=self.accent_color,
                                       selectforeground="white", bd=0,
                                       highlightthickness=0)
        self.room_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        for room in self.rooms:
            self.room_listbox.insert(tk.END, f"# {room}")
        
        self.room_listbox.bind('<<ListboxSelect>>', self.join_room)
        
        # Add room button
        add_room_btn = tk.Button(sidebar, text="+ New Room", font=("Arial", 10),
                                bg=self.secondary_color, fg="white",
                                command=self.create_room, cursor="hand2")
        add_room_btn.pack(pady=10, padx=10, fill=tk.X)
        
        # User info
        user_frame = tk.Frame(sidebar, bg=self.input_bg)
        user_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
        tk.Label(user_frame, text=f"👤 {self.username}", font=("Arial", 10),
                bg=self.input_bg, fg=self.fg_color).pack()
        
        # Right side - Chat area
        chat_container = tk.Frame(main_frame, bg=self.bg_color)
        chat_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Header
        header = tk.Frame(chat_container, bg=self.input_bg, height=50)
        header.pack(fill=tk.X, pady=(0, 5))
        header.pack_propagate(False)
        
        self.room_label = tk.Label(header, text="Select a room", font=("Arial", 14, "bold"),
                                   bg=self.input_bg, fg=self.accent_color)
        self.room_label.pack(side=tk.LEFT, padx=15, pady=10)
        
        # Online users label
        self.online_label = tk.Label(header, text="", font=("Arial", 10),
                                     bg=self.input_bg, fg="#95a5a6")
        self.online_label.pack(side=tk.RIGHT, padx=15)
        
        # Chat display
        self.chat_display = scrolledtext.ScrolledText(
            chat_container, font=("Arial", 11), bg=self.input_bg,
            fg=self.fg_color, state=tk.DISABLED, wrap=tk.WORD,
            bd=0, highlightthickness=0
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # Configure tags for styling
        self.chat_display.tag_config("username", foreground=self.accent_color, font=("Arial", 11, "bold"))
        self.chat_display.tag_config("timestamp", foreground="#95a5a6", font=("Arial", 9))
        self.chat_display.tag_config("system", foreground="#f39c12", font=("Arial", 10, "italic"))
        self.chat_display.tag_config("emoji", font=("Arial", 16))
        
        # Input area
        input_frame = tk.Frame(chat_container, bg=self.input_bg)
        input_frame.pack(fill=tk.X)
        
        # Emoji button
        emoji_btn = tk.Button(input_frame, text="😊", font=("Arial", 14),
                             bg=self.input_bg, fg=self.fg_color, bd=0,
                             command=self.show_emoji_picker, cursor="hand2")
        emoji_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # File button
        file_btn = tk.Button(input_frame, text="📎", font=("Arial", 14),
                            bg=self.input_bg, fg=self.fg_color, bd=0,
                            command=self.send_file, cursor="hand2")
        file_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Message input
        self.message_entry = tk.Entry(input_frame, font=("Arial", 12),
                                      bg="#2d2d2d", fg=self.fg_color,
                                      insertbackground=self.fg_color, bd=0)
        self.message_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=10)
        self.message_entry.bind('<Return>', lambda e: self.send_message())
        
        # Send button
        send_btn = tk.Button(input_frame, text="Send", font=("Arial", 11, "bold"),
                            bg=self.accent_color, fg="white", width=8,
                            command=self.send_message, cursor="hand2", bd=0)
        send_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Select first room
        if self.rooms:
            self.room_listbox.selection_set(0)
            self.join_room(None)
    
    def create_room(self):
        """Create a new chat room"""
        room_name = tk.simpledialog.askstring("New Room", "Enter room name:")
        if room_name:
            room_name = room_name.strip().lower().replace(' ', '_')
            if room_name and room_name not in self.rooms:
                self.rooms.append(room_name)
                self.room_listbox.insert(tk.END, f"# {room_name}")
    
    def join_room(self, event):
        """Join a chat room"""
        selection = self.room_listbox.curselection()
        if selection:
            room = self.rooms[selection[0]]
            self.current_room = room
            self.room_label.config(text=f"# {room}")
            
            # Clear chat display
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete(1.0, tk.END)
            self.chat_display.config(state=tk.DISABLED)
            
            # Send join request
            if self.socket:
                self.socket.send(json.dumps({
                    'type': 'join_room',
                    'room': room
                }).encode())
    
    def encrypt_message(self, message):
        """Encrypt message"""
        return base64.b64encode(self.cipher.encrypt(message.encode())).decode()
    
    def decrypt_message(self, encrypted_message):
        """Decrypt message"""
        try:
            return self.cipher.decrypt(base64.b64decode(encrypted_message)).decode()
        except:
            return encrypted_message
    
    def send_message(self):
        """Send text message"""
        message = self.message_entry.get().strip()
        if message and self.socket and self.current_room:
            encrypted = self.encrypt_message(message)
            self.socket.send(json.dumps({
                'type': 'text_message',
                'content': encrypted
            }).encode())
            self.message_entry.delete(0, tk.END)
    
    def send_file(self):
        """Send multimedia file"""
        if not self.current_room:
            messagebox.showwarning("Warning", "Please join a room first")
            return
        
        filepath = filedialog.askopenfilename(
            title="Select file",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.gif"), 
                      ("Videos", "*.mp4 *.avi"), 
                      ("All files", ".")]
        )
        
        if filepath:
            try:
                filename = os.path.basename(filepath)
                file_ext = os.path.splitext(filename)[1].lower()
                
                with open(filepath, 'rb') as f:
                    data = base64.b64encode(f.read()).decode()
                
                # Determine media type
                if file_ext in ['.png', '.jpg', '.jpeg', '.gif']:
                    media_type = 'image'
                elif file_ext in ['.mp4', '.avi']:
                    media_type = 'video'
                else:
                    media_type = 'file'
                
                self.socket.send(json.dumps({
                    'type': 'multimedia',
                    'media_type': media_type,
                    'data': data,
                    'filename': filename
                }).encode())
            except Exception as e:
                messagebox.showerror("Error", f"Failed to send file: {str(e)}")
    
    def show_emoji_picker(self):
        """Show emoji picker dialog"""
        if not self.current_room:
            messagebox.showwarning("Warning", "Please join a room first")
            return
        
        emoji_window = tk.Toplevel(self.root)
        emoji_window.title("Select Emoji")
        emoji_window.geometry("300x200")
        emoji_window.configure(bg=self.input_bg)
        
        frame = tk.Frame(emoji_window, bg=self.input_bg)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        for i, emoji in enumerate(self.emojis):
            btn = tk.Button(frame, text=emoji, font=("Arial", 20),
                           bg=self.input_bg, fg=self.fg_color, bd=0,
                           command=lambda e=emoji: self.send_emoji(e, emoji_window),
                           cursor="hand2")
            btn.grid(row=i//5, column=i%5, padx=5, pady=5)
    
    def send_emoji(self, emoji, window):
        """Send emoji to chat"""
        if self.socket and self.current_room:
            self.socket.send(json.dumps({
                'type': 'emoji',
                'emoji': emoji
            }).encode())
            window.destroy()
    
    def display_message(self, username, content, timestamp, msg_type='text'):
        """Display message in chat"""
        self.chat_display.config(state=tk.NORMAL)
        
        # Add timestamp
        self.chat_display.insert(tk.END, f"[{timestamp}] ", "timestamp")
        
        # Add username
        self.chat_display.insert(tk.END, f"{username}: ", "username")
        
        # Add content based on type
        if msg_type == 'text':
            self.chat_display.insert(tk.END, f"{content}\n")
        elif msg_type == 'emoji':
            self.chat_display.insert(tk.END, f"{content}\n", "emoji")
        
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
    
    def display_system_message(self, message):
        """Display system message"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"• {message}\n", "system")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
    
    def display_image(self, username, data, timestamp):
        """Display image in chat"""
        try:
            image_data = base64.b64decode(data)
            image = Image.open(io.BytesIO(image_data))
            
            # Resize if too large
            max_width = 400
            if image.width > max_width:
                ratio = max_width / image.width
                new_size = (max_width, int(image.height * ratio))
                image = image.resize(new_size, Image.LANCZOS)
            
            photo = ImageTk.PhotoImage(image)
            
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.insert(tk.END, f"[{timestamp}] ", "timestamp")
            self.chat_display.insert(tk.END, f"{username}: ", "username")
            self.chat_display.insert(tk.END, "\n")
            self.chat_display.image_create(tk.END, image=photo)
            self.chat_display.insert(tk.END, "\n")
            self.chat_display.config(state=tk.DISABLED)
            self.chat_display.see(tk.END)
            
            # Keep reference to prevent garbage collection
            if not hasattr(self, 'images'):
                self.images = []
            self.images.append(photo)
        except Exception as e:
            self.display_system_message(f"Failed to display image: {str(e)}")
    
    def show_notification(self, title, message):
        """Show desktop notification (simplified)"""
        # Flash window title for notification
        original_title = self.root.title()
        self.root.title(f"💬 New message from {message}")
        self.root.after(2000, lambda: self.root.title(original_title))
        
        # Play system bell
        self.root.bell()
    
    def receive_messages(self):
        """Receive messages from server"""
        while self.running:
            try:
                data = self.socket.recv(4096).decode()
                if not data:
                    break
                
                message = json.loads(data)
                
                if message['type'] == 'message_history':
                    # Display message history
                    self.chat_display.config(state=tk.NORMAL)
                    self.chat_display.delete(1.0, tk.END)
                    
                    for msg in message['history']:
                        username, content, msg_type, timestamp = msg
                        time_str = timestamp.split()[1] if ' ' in timestamp else timestamp
                        
                        if msg_type == 'text':
                            self.display_message(username, content, time_str)
                        elif msg_type in ['image', 'video']:
                            self.chat_display.insert(tk.END, f"[{time_str}] ", "timestamp")
                            self.chat_display.insert(tk.END, f"{username}: ", "username")
                            self.chat_display.insert(tk.END, f"[{msg_type}]\n")
                    
                    self.chat_display.config(state=tk.DISABLED)
                
                elif message['type'] == 'text_message':
                    decrypted = self.decrypt_message(message['content'])
                    self.display_message(message['username'], decrypted, 
                                       message['timestamp'])
                    
                    # Show notification if window not focused
                    if message['username'] != self.username:
                        self.show_notification("New Message", message['username'])
                
                elif message['type'] == 'emoji':
                    self.display_message(message['username'], message['emoji'],
                                       message['timestamp'], 'emoji')
                
                elif message['type'] == 'multimedia':
                    if message['media_type'] == 'image':
                        self.display_image(message['username'], message['data'],
                                         message['timestamp'])
                    else:
                        self.chat_display.config(state=tk.NORMAL)
                        self.chat_display.insert(tk.END, f"[{message['timestamp']}] ", "timestamp")
                        self.chat_display.insert(tk.END, f"{message['username']}: ", "username")
                        self.chat_display.insert(tk.END, 
                                               f"📎 {message['filename']} [{message['media_type']}]\n")
                        self.chat_display.config(state=tk.DISABLED)
                        self.chat_display.see(tk.END)
                
                elif message['type'] == 'user_joined':
                    self.display_system_message(f"{message['username']} joined the room")
                    self.online_label.config(text=f"👥 {len(message['users'])} online")
                
                elif message['type'] == 'user_left':
                    self.display_system_message(f"{message['username']} left the room")
            
            except Exception as e:
                if self.running:
                    print(f"Error receiving message: {e}")
                break
    
    def on_closing(self):
        """Handle window closing"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.root.destroy()

def main():
    root = tk.Tk()
    app = ChatClient(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == '_main_':
    main()