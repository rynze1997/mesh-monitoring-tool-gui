import serial
import serial.tools.list_ports
import time

class USBManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(USBManager, cls).__new__(cls)
            # Put any initialization here.
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):  # Prevents reinitialization
            self.ser = None
            self.initialized = True

    def initiate_connection(self, device_description="Monitoring-tool", baud_rate=115200, timeout=2):
        if self.ser is None:  # Only initiate if not already done
            monitoring_tool_port = None
            ports = serial.tools.list_ports.comports()
            for port, desc, hwid in sorted(ports):
                if device_description in desc:
                    monitoring_tool_port = port
                    break
            if monitoring_tool_port:
                self.ser = serial.Serial(monitoring_tool_port, baud_rate, timeout=timeout)
                print(f"Connected to {device_description}, port: {monitoring_tool_port}")
                time.sleep(2)
                return True
            else:
                print(f"{device_description} not found")
                return False

    def clear_buffer(self):
        if self.ser:
            self.ser.read_all()

    def send_data(self, data):
        if self.ser:
            self.ser.write(data)
            
    def receive_data(self):
        start_delimiter = self.ser.read_until("PLEJD".encode("utf-8"))
        if start_delimiter == b'':
            return None, None
        incoming_bytes = self.ser.read_until("END".encode("utf-8"))
        return incoming_bytes
