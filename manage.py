import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText
import paramiko
import threading
import time
import csv
import os
import datetime
import subprocess
import socket
import sys
import sqlite3
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
from urllib.parse import urlparse

def get_resource_path(filename):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.abspath("."), filename)

# Initialize encryption key
def get_encryption_key():
    key_file = get_resource_path("key.key")
    if not os.path.exists(key_file):
        key = Fernet.generate_key()
        with open(key_file, "wb") as f:
            f.write(key)
    with open(key_file, "rb") as f:
        return f.read()

# Initialize SQLite database
def init_database():
    conn = sqlite3.connect(get_resource_path("servers.db"))
    cursor = conn.cursor()
    # Servers table for credentials
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS servers (
            server_ip TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )
    """)
    # Channels table for processed CSV data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            lcn TEXT PRIMARY KEY,
            server_ip TEXT NOT NULL,
            channel_name TEXT NOT NULL,
            udp_ip TEXT NOT NULL,
            udp_port TEXT NOT NULL,
            http_url TEXT NOT NULL
        )
    """)
    # Settings table for VLC path
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

class SSHExecutorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LCN Channel Restart Tool")
        icon_path = get_resource_path("Lyvelogo.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        # Initialize database first
        init_database()

        # Load VLC path from database, default to "vlc" if not set
        conn = sqlite3.connect(get_resource_path("servers.db"))
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'vlc_path'")
        result = cursor.fetchone()
        self.vlc_path = result[0] if result else "vlc"
        conn.close()

        self.fernet = Fernet(get_encryption_key())  # Initialize Fernet for encryption

        top_frame = ttk.Frame(root)
        top_frame.pack(fill="x", padx=10, pady=10)

        ttk.Button(top_frame, text="Process Raw CSV", command=self.process_raw_csv).pack(side="left", padx=5)
        ttk.Button(top_frame, text="Select VLC", command=self.select_vlc).pack(side="left", padx=5)
        ttk.Button(top_frame, text="Manage Servers", command=self.manage_servers).pack(side="left", padx=5)

        ttk.Label(top_frame, text="LCN:").pack(side="left", padx=(20, 5))
        self.lcn_entry = ttk.Entry(top_frame, width=10)
        self.lcn_entry.pack(side="left", padx=5)
        self.lcn_entry.bind("<Return>", lambda e: self.auto_check_status())

        self.execute_btn = ttk.Button(top_frame, text="Execute", command=self.run_command)
        self.execute_btn.pack(side="left", padx=5)

        self.play_udp_btn = ttk.Button(top_frame, text="Play UDP", command=self.play_udp)
        self.play_udp_btn.pack(side="left", padx=5)

        self.play_http_btn = ttk.Button(top_frame, text="Play HTTP", command=self.play_http)
        self.play_http_btn.pack(side="left", padx=5)

        self.status_label = ttk.Label(top_frame, text="Status: Unknown")
        self.status_label.pack(side="left", padx=10)

        self.progress = ttk.Progressbar(top_frame, mode='indeterminate', length=150)
        self.progress.pack(side="left", padx=10)

        self.output_box = ScrolledText(root, wrap=tk.WORD, height=20, state=tk.DISABLED)
        self.output_box.pack(fill="both", expand=True, padx=10, pady=10)
        self.output_box.tag_config("error", foreground="red")
        self.output_box.tag_config("bold", font=('TkDefaultFont', 10, 'bold'))

        bottom_frame = ttk.Frame(root)
        bottom_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(bottom_frame, text="View Logs", command=self.view_logs).pack(side="left", padx=5)
        ttk.Button(bottom_frame, text="Clear Logs", command=self.clear_logs).pack(side="left", padx=5)

    def process_raw_csv(self):
        file_path = filedialog.askopenfilename(filetypes=[["CSV Files", "*.csv"]])
        if not file_path:
            return

        try:
            processed_data = []
            with open(file_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    # Extract required fields
                    lcn = row.get("channel_number", "").strip()
                    channel_name = row.get("channel_name", "Unknown").strip()
                    input_url = row.get("input_url", "").strip()
                    udp_port = row.get("input_port", "").strip()
                    channel_ott_url = row.get("channel_ott_url", "").strip()

                    # Validate required fields
                    if not lcn or not input_url or not udp_port or not channel_ott_url:
                        continue

                    # Extract udp_ip from input_url (content after udp://@)
                    if input_url.startswith("udp://@"):
                        udp_ip = input_url[len("udp://@"):]
                    else:
                        continue  # Skip invalid input_url

                    # Extract server_ip from channel_ott_url
                    parsed_url = urlparse(channel_ott_url)
                    server_ip = parsed_url.hostname
                    if not server_ip:
                        continue  # Skip if no hostname/IP found

                    # Construct http_url
                    http_url = f"http://223.29.207.134:4022/udp/{udp_ip}:{udp_port}"

                    # Add to processed data
                    processed_data.append({
                        "lcn": lcn,
                        "server_ip": server_ip,
                        "channel_name": channel_name,
                        "udp_ip": udp_ip,
                        "udp_port": udp_port,
                        "http_url": http_url
                    })

            # Save to database
            conn = sqlite3.connect(get_resource_path("servers.db"))
            cursor = conn.cursor()
            # Truncate existing channels table
            cursor.execute("DELETE FROM channels")
            # Insert new data
            for data in processed_data:
                cursor.execute("""
                    INSERT INTO channels (lcn, server_ip, channel_name, udp_ip, udp_port, http_url)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    data["lcn"],
                    data["server_ip"],
                    data["channel_name"],
                    data["udp_ip"],
                    data["udp_port"],
                    data["http_url"]
                ))
            conn.commit()
            conn.close()

            messagebox.showinfo("Success", "Raw CSV processed and saved to database.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process CSV: {e}")

    def get_channel_data(self, lcn):
        conn = sqlite3.connect(get_resource_path("servers.db"))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT server_ip, channel_name, udp_ip, udp_port, http_url
            FROM channels WHERE lcn = ?
        """, (lcn,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return {
                "server_ip": result[0],
                "channel_name": result[1],
                "udp_ip": result[2],
                "udp_port": result[3],
                "http_url": result[4]
            }
        return None

    def get_server_credentials(self, server_ip):
        conn = sqlite3.connect(get_resource_path("servers.db"))
        cursor = conn.cursor()
        cursor.execute("SELECT username, password FROM servers WHERE server_ip = ?", (server_ip,))
        result = cursor.fetchone()
        conn.close()
        if result:
            username, encrypted_password = result
            try:
                password = self.fernet.decrypt(encrypted_password.encode()).decode()
                return username, password
            except Exception as e:
                messagebox.showerror("Error", f"Failed to decrypt password: {e}")
                return None, None
        return None, None

    def manage_servers(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Manage Servers")
        dialog.geometry("600x400")

        # Treeview to display servers
        tree = ttk.Treeview(dialog, columns=("server_ip", "username"), show="headings")
        tree.heading("server_ip", text="Server IP")
        tree.heading("username", text="Username")
        tree.pack(fill="both", expand=True, padx=10, pady=10)

        # Load existing servers
        conn = sqlite3.connect(get_resource_path("servers.db"))
        cursor = conn.cursor()
        cursor.execute("SELECT server_ip, username FROM servers")
        for row in cursor.fetchall():
            tree.insert("", tk.END, values=row)
        conn.close()

        # Buttons frame
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill="x", padx=10, pady=10)

        def add_server():
            add_dialog = tk.Toplevel(dialog)
            add_dialog.title("Add Server")
            add_dialog.geometry("400x300")

            # Use a frame with grid layout
            form_frame = ttk.Frame(add_dialog)
            form_frame.pack(padx=10, pady=10, fill="both")

            # Server IP
            ttk.Label(form_frame, text="Server IP:").grid(row=0, column=0, sticky="w", pady=5)
            server_ip_entry = ttk.Entry(form_frame)
            server_ip_entry.grid(row=0, column=1, sticky="ew", pady=5)

            # Username
            ttk.Label(form_frame, text="Username:").grid(row=1, column=0, sticky="w", pady=5)
            username_entry = ttk.Entry(form_frame)
            username_entry.grid(row=1, column=1, sticky="ew", pady=5)

            # Password
            ttk.Label(form_frame, text="Password:").grid(row=2, column=0, sticky="w", pady=5)
            password_entry = ttk.Entry(form_frame, show="*")
            password_entry.grid(row=2, column=1, sticky="ew", pady=5)

            # Configure grid weights
            form_frame.columnconfigure(1, weight=1)

            # Buttons frame
            button_frame = ttk.Frame(add_dialog)
            button_frame.pack(pady=10)

            def save_server():
                server_ip = server_ip_entry.get().strip()
                username = username_entry.get().strip()
                password = password_entry.get().strip()
                if not all([server_ip, username, password]):
                    messagebox.showerror("Error", "All fields are required.")
                    return
                try:
                    encrypted_password = self.fernet.encrypt(password.encode()).decode()
                    conn = sqlite3.connect(get_resource_path("servers.db"))
                    cursor = conn.cursor()
                    cursor.execute("INSERT OR REPLACE INTO servers (server_ip, username, password) VALUES (?, ?, ?)",
                                   (server_ip, username, encrypted_password))
                    conn.commit()
                    conn.close()
                    tree.insert("", tk.END, values=(server_ip, username))
                    messagebox.showinfo("Success", "Server added successfully!")
                    add_dialog.destroy()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to add server: {e}")

            # Save and Cancel buttons
            ttk.Button(button_frame, text="Save", command=save_server).pack(side="left", padx=5)
            ttk.Button(button_frame, text="Cancel", command=add_dialog.destroy).pack(side="left", padx=5)

            add_dialog.transient(dialog)
            add_dialog.grab_set()

        def delete_server():
            selected = tree.selection()
            if not selected:
                messagebox.showerror("Error", "Select a server to delete.")
                return
            server_ip = tree.item(selected[0])["values"][0]
            if messagebox.askyesno("Confirm", f"Delete server {server_ip}?"):
                conn = sqlite3.connect(get_resource_path("servers.db"))
                cursor = conn.cursor()
                cursor.execute("DELETE FROM servers WHERE server_ip = ?", (server_ip,))
                conn.commit()
                conn.close()
                tree.delete(selected[0])
                messagebox.showinfo("Success", "Server deleted successfully!")

        ttk.Button(btn_frame, text="Add Server", command=add_server).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Delete Server", command=delete_server).pack(side="left", padx=5)

        dialog.transient(self.root)
        dialog.grab_set()

    def run_command(self):
        def worker(profile, lcn):
            server_ip = profile["server_ip"]
            channel_name = profile.get("channel_name", "Unknown")
            port = 22
            command = f"cd xcoder && ./transcoderresetiptv.sh {lcn}"
            timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")

            log_file = f"command_log_{datetime.date.today().isoformat()}.txt"

            username, password = self.get_server_credentials(server_ip)
            if not username or not password:
                messagebox.showerror("Error", f"No credentials found for server {server_ip}.")
                self.progress.stop()
                self.execute_btn.config(state=tk.NORMAL)
                return

            try:
                self.progress.start()
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(server_ip, port=port, username=username, password=password)

                full_cmd = f"sudo -S bash -c '{command}'"
                stdin, stdout, stderr = ssh.exec_command(full_cmd, get_pty=True)

                stdin.write(password + "\n")
                stdin.flush()

                self.output_box.config(state=tk.NORMAL)
                self.output_box.insert(tk.END, f"\n{timestamp} {command}\n", "bold")
                self.output_box.see(tk.END)

                output = ""
                for line in iter(lambda: stdout.readline(), ""):
                    output += line
                    self.output_box.insert(tk.END, line)
                    self.output_box.see(tk.END)
                    self.output_box.update()

                err = stderr.read().decode()
                if err:
                    self.output_box.insert(tk.END, "\nErrors:\n", "error")
                    self.output_box.insert(tk.END, err, "error")

                self.output_box.insert(tk.END, "\n")
                self.output_box.config(state=tk.DISABLED)
                ssh.close()

                with open(log_file, "a", encoding="utf-8", errors="ignore") as f:
                    f.write(f"{timestamp} | Server: {server_ip} | LCN: {lcn}\n")
                    f.write(f"Command: {command}\n")
                    f.write(f"Output:\n{output}\n")
                    if err:
                        f.write(f"Errors:\n{err}\n")
                    f.write("-" * 60 + "\n")

                self.show_restart_popup(channel_name)
            except Exception as e:
                messagebox.showerror("SSH Error", str(e))
            finally:
                self.progress.stop()
                self.execute_btn.config(state=tk.NORMAL)

        lcn = self.lcn_entry.get().strip()
        profile = self.get_channel_data(lcn)
        if not profile:
            messagebox.showerror("Error", f"LCN {lcn} not found in database.")
            return

        self.execute_btn.config(state=tk.DISABLED)
        threading.Thread(target=worker, args=(profile, lcn)).start()

    def play_udp(self):
        lcn = self.lcn_entry.get().strip()
        channel_data = self.get_channel_data(lcn)
        if not channel_data:
            messagebox.showerror("UDP Error", f"No channel data found for LCN {lcn}.")
            return
        udp_url = f"udp://@{channel_data['udp_ip']}:{channel_data['udp_port']}"
        try:
            subprocess.Popen([self.vlc_path, udp_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            messagebox.showerror("VLC Error", "VLC not found. Select it using 'Select VLC'.")

    def play_http(self):
        lcn = self.lcn_entry.get().strip()
        channel_data = self.get_channel_data(lcn)
        if not channel_data:
            messagebox.showerror("HTTP Error", f"No channel data found for LCN {lcn}.")
            return
        http_url = channel_data["http_url"]
        try:
            subprocess.Popen([self.vlc_path, http_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            messagebox.showerror("VLC Error", "VLC not found. Select it using 'Select VLC'.")

    def select_vlc(self):
        path = filedialog.askopenfilename(filetypes=[["VLC Executable", "vlc.exe" if os.name == 'nt' else "vlc"]])
        if path:
            self.vlc_path = path
            # Save to database
            try:
                conn = sqlite3.connect(get_resource_path("servers.db"))
                cursor = conn.cursor()
                cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ("vlc_path", path))
                conn.commit()
                conn.close()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save VLC path: {e}")

    def view_logs(self):
        log_file = f"command_log_{datetime.date.today().isoformat()}.txt"
        if os.path.exists(log_file):
            try:
                if os.name == 'nt':
                    os.startfile(log_file)
                else:
                    subprocess.run(["xdg-open", log_file])
            except Exception as e:
                messagebox.showerror("Log Viewer Error", str(e))
        else:
            messagebox.showinfo("No Logs", "No log file found for today.")

    def clear_logs(self):
        log_file = f"command_log_{datetime.date.today().isoformat()}.txt"
        if os.path.exists(log_file):
            try:
                with open(log_file, "w", encoding="utf-8") as f:
                    f.write("")
                messagebox.showinfo("Logs Cleared", "Log file cleared.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear log:\n{e}")
        else:
            messagebox.showinfo("No Logs", "No log file to clear.")

    def show_restart_popup(self, channel_name):
        self.root.after(100, lambda: messagebox.showinfo("Success", f'Channel restarted: "{channel_name}"'))

    def auto_check_status(self):
        lcn = self.lcn_entry.get().strip()
        channel_data = self.get_channel_data(lcn)
        if not channel_data:
            self.status_label.config(text="Status: Unknown ❓", foreground="gray")
            return

        http_url = channel_data["http_url"]
        udp_url = f"udp://@{channel_data['udp_ip']}:{channel_data['udp_port']}"

        def check_url(url):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM if url.startswith("udp://") else socket.SOCK_STREAM)
                sock.settimeout(2)
                host = url.split("@")[-1].split(":")[0] if url.startswith("udp") else url.split("//")[1].split(":")[0]
                port = int(url.split(":")[-1])
                sock.connect((host, port))
                sock.close()
                return True
            except Exception:
                return False

        status = "OK ✅" if (http_url and check_url(http_url)) or (udp_url and check_url(udp_url)) else "Offline ❌"
        self.status_label.config(text=f"Status: {status}", foreground="green" if "OK" in status else "red")

if __name__ == "__main__":
    root = tk.Tk()
    app = SSHExecutorApp(root)
    root.mainloop()