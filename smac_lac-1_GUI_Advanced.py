import serial
import serial.tools.list_ports
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime
import threading

class LAC1BackupRestoreApp:
    def __init__(self, master):
        self.master = master
        master.title("LAC-1 Backup & Restore Tool")
        master.geometry("700x500")

        frame = tk.Frame(master)
        frame.pack(pady=10)

        self.port_label = tk.Label(frame, text="Serial Port:")
        self.port_label.grid(row=0, column=0, padx=5)

        self.port_combo = ttk.Combobox(frame, width=15)
        self.port_combo.grid(row=0, column=1, padx=5)

        self.scan_button = tk.Button(frame, text="Scan Ports", command=self.scan_ports)
        self.scan_button.grid(row=0, column=2, padx=5)

        self.baudrate_label = tk.Label(frame, text="Baudrate:")
        self.baudrate_label.grid(row=0, column=3, padx=5)

        self.baudrate_entry = tk.Entry(frame, width=10)
        self.baudrate_entry.insert(0, "9600")
        self.baudrate_entry.grid(row=0, column=4, padx=5)

        self.backup_button = tk.Button(master, text="Backup LAC-1", command=self.backup_lac1)
        self.backup_button.pack(pady=5)

        self.restore_button = tk.Button(master, text="Restore to LAC-1", command=self.restore_lac1)
        self.restore_button.pack(pady=5)

        self.progress = ttk.Progressbar(master, orient='horizontal', length=600, mode='determinate')
        self.progress.pack(pady=10)

        self.log_text = tk.Text(master, height=15, width=80)
        self.log_text.pack(pady=10)

        self.status_label = tk.Label(master, text="Status: Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(fill=tk.X, side=tk.BOTTOM, ipady=2)

    def log(self, message, color="black"):
        self.log_text.insert(tk.END, message + '\n')
        self.log_text.tag_add(color, "end-2l", "end-1l")
        self.log_text.tag_config(color, foreground=color)
        self.log_text.see(tk.END)

    def set_status(self, text):
        self.status_label.config(text=f"Status: {text}")

    def scan_ports(self):
        ports = serial.tools.list_ports.comports()
        port_list = [port.device for port in ports]
        self.port_combo['values'] = port_list
        if port_list:
            self.port_combo.current(0)

    def backup_lac1(self):
        threading.Thread(target=self._backup_lac1).start()

    def restore_lac1(self):
        threading.Thread(target=self._restore_lac1).start()

    def _open_serial(self, port, baudrate):
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )
        time.sleep(2)
        ser.write(b'\x1b')  # ESC to get prompt
        time.sleep(0.5)
        if b'>' not in ser.read(100):
            ser.close()
            raise Exception("No response from LAC-1 (no '>' prompt)")
        return ser

    def _backup_lac1(self):
        port = self.port_combo.get()
        baudrate = int(self.baudrate_entry.get())
        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=f"lac1_backup_{now}.txt")
        if not file_path:
            return

        try:
            self.set_status("Connecting...")
            self.log(f"Connecting to {port}...", "blue")
            ser = self._open_serial(port, baudrate)

            with open(file_path, 'w') as f:
                self.set_status("Backing up macros...")
                self.log("Backing up macros (TM-1)...", "blue")
                ser.write(b'TM-1\r')
                self.log(">>> TM-1", "blue")
                time.sleep(0.5)
                tm_response = ser.read(8192).decode(errors='ignore')
                self.log("<<< TM-1 Response Captured", "green")
                f.write('--- MACROS (TM-1) ---\n')
                f.write(tm_response)
                f.write('\n\n')

                self.set_status("Backing up system parameters...")
                self.log("Backing up system parameters (TK1)...", "blue")
                ser.write(b'TK1\r')
                self.log(">>> TK1", "blue")
                time.sleep(0.5)
                tk1_response = ser.read(4096).decode(errors='ignore')
                self.log("<<< TK1 Response Captured", "green")
                f.write('--- SYSTEM PARAMETERS (TK1) ---\n')
                f.write(tk1_response)
                f.write('\n\n')

                self.set_status("Backing up registers...")
                self.log("Backing up registers (TR0 to TR511)...", "blue")
                f.write('--- REGISTERS (TR0 to TR511) ---\n')
                for i in range(512):
                    command = f'TR{i}\r'.encode()
                    ser.write(command)
                    self.log(f">>> TR{i}", "blue")
                    time.sleep(0.05)
                    tr_response = ser.readline().decode(errors='ignore').strip()
                    self.log(f"<<< {tr_response}", "green")
                    f.write(f'TR{i}: {tr_response}\n')
                    self.progress['value'] = (i / 511) * 100
                    self.master.update_idletasks()

            ser.close()
            self.set_status("Backup completed.")
            self.progress['value'] = 0
            messagebox.showinfo("Backup Completed", f"Backup saved as {file_path}")

        except Exception as e:
            self.log(f"Error: {e}", "red")
            self.set_status("Error")

    def _restore_lac1(self):
        port = self.port_combo.get()
        baudrate = int(self.baudrate_entry.get())
        file_path = filedialog.askopenfilename(title="Select Backup File", filetypes=(('Text files', '*.txt'),))
        if not file_path:
            return

        try:
            self.set_status("Connecting...")
            self.log(f"Connecting to {port}...", "blue")
            ser = self._open_serial(port, baudrate)

            with open(file_path, 'r') as f:
                lines = f.readlines()

            in_macro_section = False
            in_register_section = False

            total_commands = sum(1 for line in lines if line.strip() and (line.startswith('MD') or line.startswith('>') or line.startswith('TR')))
            processed_commands = 0

            for line in lines:
                line = line.strip()

                if line.startswith('--- MACROS'):
                    in_macro_section = True
                    in_register_section = False
                    continue
                elif line.startswith('--- SYSTEM PARAMETERS'):
                    in_macro_section = False
                    in_register_section = False
                    continue
                elif line.startswith('--- REGISTERS'):
                    in_macro_section = False
                    in_register_section = True
                    continue

                if in_macro_section and line:
                    if not line.startswith('MD') and not line.startswith('>'):
                        continue
                    command = line.replace('>', '').strip() + '\r'
                    ser.write(command.encode())
                    self.log(f">>> {command.strip()}", "blue")
                    time.sleep(0.1)

                if in_register_section and line:
                    if line.startswith('TR') and ':' in line:
                        reg_num, value = line.split(':', 1)
                        reg_index = reg_num.replace('TR', '').strip()
                        value = value.strip()
                        if value.isdigit():
                            cmd = f'AL{value},AR{reg_index}\r'
                            ser.write(cmd.encode())
                            self.log(f">>> AL{value},AR{reg_index}", "blue")
                            time.sleep(0.05)

                processed_commands += 1
                self.progress['value'] = (processed_commands / total_commands) * 100
                self.master.update_idletasks()

            ser.close()
            self.set_status("Restore completed.")
            self.progress['value'] = 0
            messagebox.showinfo("Restore Completed", f"Restored from {file_path}")

        except Exception as e:
            self.log(f"Error: {e}", "red")
            self.set_status("Error")

if __name__ == "__main__":
    root = tk.Tk()
    app = LAC1BackupRestoreApp(root)
    root.mainloop()