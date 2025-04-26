import serial
import time

def backup_lac1(port='COM10', baudrate=9600, output_file='lac1_backup.txt'):
    try:
        # Open the serial port
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )

        time.sleep(2)  # Wait a bit after opening

        with open(output_file, 'w') as f:
            # Send and capture TM-1 (dump all macros)
            ser.write(b'TM-1\r')
            time.sleep(0.5)
            tm_response = ser.read(4096).decode(errors='ignore')
            f.write('--- MACROS (TM-1) ---\n')
            f.write(tm_response)
            f.write('\n\n')

            # Send and capture TK1 (system parameters)
            ser.write(b'TK1\r')
            time.sleep(0.5)
            tk1_response = ser.read(4096).decode(errors='ignore')
            f.write('--- SYSTEM PARAMETERS (TK1) ---\n')
            f.write(tk1_response)
            f.write('\n\n')

            # Loop through TR0 to TR511 (Registers)
            f.write('--- REGISTERS (TR0 to TR511) ---\n')
            for i in range(512):
                command = f'TR{i}\r'.encode()
                ser.write(command)
                time.sleep(0.05)
                tr_response = ser.readline().decode(errors='ignore').strip()
                f.write(f'TR{i}: {tr_response}\n')

        ser.close()
        print(f"Backup completed successfully. Saved to {output_file}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    backup_lac1(port='COM10', baudrate=9600, output_file='lac1_backup.txt')
