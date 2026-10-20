import serial
import time
import threading
from typing import Dict, Any, Optional

class STM32SerialController:
    """
    Manages USB Serial communication between Laptop 2 and the STM32 Blue Pill.
    Includes hardware protocol parsing and simulation mode.
    """
    def __init__(self):
        self.ser: Optional[serial.Serial] = None
        self.is_connected = False
        self.port = ""
        self.baud = 115200
        self.last_raw_packet = ""
        
    def connect(self, port: str, baud_rate: int = 115200) -> str:
        """Establishes connection with the STM32 Blue Pill."""
        self.port = port
        self.baud = baud_rate
        
        # Simulation Mode trigger for offline testing
        if port.upper() == "SIMULATION":
            self.is_connected = True
            return "SIMULATION_MODE_ACTIVE"
            
        try:
            self.ser = serial.Serial(port, baud_rate, timeout=0.1)
            time.sleep(1.5)  # Stabilization delay
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            self.is_connected = True
            return f"CONNECTED_SUCCESS: {port}"
        except serial.SerialException as e:
            self.is_connected = False
            return f"ERROR: Could not open {port} ({str(e)})"

    def disconnect(self):
        """Closes serial connection."""
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.is_connected = False

    def send_command(self, payload: str) -> str:
        """Sends framed packet to STM32: <HEADER>|<COMMAND>|<DATA>\n"""
        if not self.is_connected:
            return "ERROR: Serial Not Connected"
            
        full_packet = f"BGUI|{payload}\n"
        
        if self.port.upper() == "SIMULATION":
            return f"TX_SUCCESS (SIMULATED): {full_packet.strip()}"
            
        try:
            self.ser.write(full_packet.encode('utf-8'))
            self.ser.flush()
            return f"TX_SUCCESS: {full_packet.strip()}"
        except serial.SerialException as e:
            return f"TX_ERROR: {str(e)}"

    def read_incoming_telemetry(self) -> Dict[str, Any]:
        """
        Polls line-buffered serial data from STM32 and updates state dict.
        """
        data_event = {
            "has_data": False,
            "raw": "",
            "event_type": None,
            "payload": ""
        }
        
        if not self.is_connected or self.port.upper() == "SIMULATION":
            return data_event

        try:
            if self.ser.in_waiting > 0:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    data_event["has_data"] = True
                    data_event["raw"] = line
                    self.last_raw_packet = line
                    
                    # Protocol Parsing: HEADER|EVENT|DATA or RAW_EVENT
                    parts = line.split("|")
                    if len(parts) >= 2:
                        data_event["event_type"] = parts[1]
                        data_event["payload"] = parts[2] if len(parts) > 2 else ""
                    else:
                        data_event["event_type"] = line
        except serial.SerialException:
            pass

        return data_event

# Global Instance
stm32_controller = STM32SerialController()

def send_payment_confirmation(destination: str) -> str:
    """Helper function to issue payment confirmation to STM32."""
    return stm32_controller.send_command(f"PAYMENT_CONFIRMED|{destination}")

def send_system_reset() -> str:
    """Helper function to issue system reset to STM32."""
    return stm32_controller.send_command("SYSTEM_RESET")