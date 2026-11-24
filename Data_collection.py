import socket
import time
import numpy as np
import serial
import serial.tools.list_ports
import json
import struct
from datetime import datetime

class RadarDataReceiver:
    def __init__(self, host='0.0.0.0', port=12345):
        # Radar configuration (matches paper specs)
        self.center_freq = 62e9  # 60-64 GHz
        self.bandwidth = 4e9
        self.chirp_duration = 50e-6  # 50 μs
        self.num_samples = 256
        self.num_chirps = 64
        self.num_rx = 3
        self.fs = 10e6  # 10 MSPS
        
        # Networking setup
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        
        # Hardware connection
        self.serial_port = None
        self.connect_to_radar()
        
    def connect_to_radar(self):
        """Automatically detect and connect to radar hardware"""
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if 'ACM' in port.device or 'USB' in port.description:
                try:
                    self.serial_port = serial.Serial(
                        port.device, 
                        baudrate=921600, 
                        timeout=1
                    )
                    print(f"Connected to radar at {port.device}")
                    return
                except serial.SerialException:
                    continue
        print("No radar hardware found - running in simulation mode")
    
    def read_frame(self):
        """Read a frame of radar data"""
        frame_size = self.num_chirps * self.num_rx * self.num_samples * 4
        
        if self.serial_port:
            # Read from actual hardware
            data = self.serial_port.read(frame_size)
            if len(data) != frame_size:
                return None
            return data
        else:
            # Generate simulated data
            return np.random.randn(frame_size).tobytes()
    
    def start(self):
        """Main receiver loop"""
        print(f"Radar receiver started on {self.host}:{self.port}")
        print("Waiting for processor to connect...")
        
        conn, addr = self.server_socket.accept()
        print(f"Processor connected from {addr}")
        
        frame_count = 0
        try:
            while True:
                start_time = time.time()
                
                # Read radar data
                raw_data = self.read_frame()
                if raw_data is None:
                    time.sleep(0.01)
                    continue
                
                # Create metadata
                timestamp = datetime.utcnow().isoformat()
                metadata = {
                    'frame_id': frame_count,
                    'timestamp': timestamp,
                    'config': {
                        'center_freq': self.center_freq,
                        'bandwidth': self.bandwidth,
                        'chirp_duration': self.chirp_duration,
                        'num_samples': self.num_samples,
                        'num_chirps': self.num_chirps,
                        'num_rx': self.num_rx,
                        'fs': self.fs
                    }
                }
                
                # Send data to processor
                header = json.dumps(metadata).encode('utf-8')
                conn.send(struct.pack('!I', len(header)))  # Header length
                conn.send(header)                         # Header content
                conn.send(raw_data)                       # Binary payload
                
                frame_count += 1
                elapsed = time.time() - start_time
                sleep_time = max(0.05 - elapsed, 0.001)  # Maintain ~20 FPS
                time.sleep(sleep_time)
                
        except (ConnectionResetError, BrokenPipeError):
            print("Processor disconnected")
        finally:
            conn.close()
            if self.serial_port:
                self.serial_port.close()

if __name__ == "__main__":
    receiver = RadarDataReceiver()
    receiver.start()