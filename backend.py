import serial
import time

def send_bus_stop_request(port: str, baud_rate: int = 115200, timeout: float = 3.0) -> str:
    """
    Sends the BUS_STOP_REQUEST command packet over USB Serial to the ESP32 
    and reads the resulting status response.
    """
    # Packet structured per system design protocol: <HEADER>|<COMMAND>|<DATA>
    payload = "BGUI|BUS_STOP_REQUEST|DEMO_STOP\n"
    
    try:
        with serial.Serial(port, baud_rate, timeout=timeout) as ser:
            # Allow time for serial DTR toggle / line stabilization
            time.sleep(1.5)
            
            # Flush any residual buffer data
            ser.reset_input_buffer()
            
            # Transmit command to ESP32
            ser.write(payload.encode('utf-8'))
            
            # Read response string returned by ESP32 (e.g., TX_SUCCESS or TX_FAILED)
            response = ser.readline().decode('utf-8').strip()
            
            if not response:
                return "ERROR: Serial Timeout - No response from ESP32"
                
            return response

    except serial.SerialException as e:
        return f"ERROR: Unable to open port {port} ({str(e)})"