import serial
import time

def restore_lac1(backup_file='lac1_backup.txt', port='COM10', baudrate=9600):
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

        time.sleep(2)  # Give some time after opening

        with open(backup_file, 'r') as f:
            lines = f.readlines()

        # Flags to detect sections
        in_macro_section = False
        in_register_section = False

        for line in lines:
            line = line.strip()

            # Detect sections
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

            # Send back macros line-by-line
            if in_macro_section and line:
                # Skip comments and empty lines
                if not line.startswith('MD') and not line.startswith('>'):
                    continue
                # Send macro define lines
                command = line.replace('>', '').strip() + '\r'
                ser.write(command.encode())
                time.sleep(0.1)

            # Restore register values
            if in_register_section and line:
                if line.startswith('TR') and ':' in line:
                    reg_num, value = line.split(':', 1)
                    reg_index = reg_num.replace('TR', '').strip()
                    value = value.strip()
                    if value.isdigit():
                        cmd = f'AL{value},AR{reg_index}\r'
                        ser.write(cmd.encode())
                        time.sleep(0.05)

        ser.close()
        print(f"Restore completed successfully from {backup_file}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    restore_lac1(backup_file='lac1_backup.txt', port='COM10', baudrate=9600)
