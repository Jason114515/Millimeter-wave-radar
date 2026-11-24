import socket
import json
import struct
import numpy as np
from scipy.fft import fft, fftfreq, fftshift
from sklearn.cluster import DBSCAN
import time

class RadarProcessor:
    def __init__(self, host='127.0.0.1', port=12345):
        # Networking setup
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Processing state
        self.background = None
        self.clutter_alpha = 0.05  # Background learning rate
    
    def connect(self):
        """Connect to radar receiver"""
        self.sock.connect((self.host, self.port))
        print(f"Connected to radar receiver at {self.host}:{self.port}")
    
    def receive_frame(self):
        """Receive a complete frame from receiver"""
        try:
            # Read header length (4 bytes)
            header_len_bytes = self.sock.recv(4)
            if len(header_len_bytes) != 4:
                raise ValueError("Incomplete header length received")
        
            header_len = struct.unpack('!I', header_len_bytes)[0]
        
            # Read header content in chunks if necessary
            header_data = b''
            while len(header_data) < header_len:
                chunk = self.sock.recv(header_len - len(header_data))
                if not chunk:
                    raise ConnectionError("Connection lost while receiving header")
                header_data += chunk
        
            # Decode and parse JSON header
            try:
                header = json.loads(header_data.decode('utf-8'))
            except UnicodeDecodeError:
                # Fallback to latin-1 if UTF-8 fails
                header = json.loads(header_data.decode('latin-1'))
        
            # Read binary payload in chunks
            frame_size = (header['config']['num_chirps'] * 
                         header['config']['num_rx'] * 
                        header['config']['num_samples'] * 4)
        
            raw_data = b''
            while len(raw_data) < frame_size:
                chunk = self.sock.recv(frame_size - len(raw_data))
                if not chunk:
                    raise ConnectionError("Connection lost while receiving frame data")
                raw_data += chunk
        
            # Convert to complex64 numpy array
            iq_data = np.frombuffer(raw_data, dtype=np.int16)
            complex_data = iq_data.astype(np.float32).view(np.complex64)
        
            return header, complex_data
        
        except Exception as e:
            print(f"Error receiving frame: {str(e)}")
            raise
    
    def range_fft(self, data, num_samples):
        """Perform range FFT processing"""
        window = np.hamming(num_samples)
        windowed = data * window
        return fft(windowed, axis=2)
    
    def doppler_processing(self, data, num_chirps):
        """Perform Doppler processing"""
        window = np.hamming(num_chirps)
        windowed = data * window[:, np.newaxis, np.newaxis]
        return fftshift(fft(windowed, axis=0), axes=0)
    
    def clutter_suppression(self, data):
        """Adaptive clutter suppression"""
        if self.background is None:
            self.background = np.mean(data, axis=0)
            return np.zeros_like(data)
        
        foreground = data - self.background
        self.background = (1 - self.clutter_alpha) * self.background + self.clutter_alpha * data
        return foreground
    
    def detect_targets(self, data, config):
        """Detect and cluster targets"""
        # Reshape to (chirps, rx, samples)
        reshaped = data.reshape(
            config['num_chirps'], 
            config['num_rx'], 
            config['num_samples']
        )
        
        # Signal processing pipeline
        range_fft = self.range_fft(reshaped, config['num_samples'])
        doppler_fft = self.doppler_processing(range_fft, config['num_chirps'])
        clutter_suppressed = self.clutter_suppression(doppler_fft)
        
        # Target detection
        power = np.abs(clutter_suppressed)
        threshold = np.percentile(power, 95) * 0.5
        peaks = np.where(power > threshold)
        
        # Collect detections
        detections = []
        for i in range(len(peaks[0])):
            chirp_idx = peaks[0][i]
            rx_idx = peaks[1][i]
            sample_idx = peaks[2][i]
            
            # Convert to physical units
            range_val = sample_idx * (3e8 / (2 * config['bandwidth']))
            velocity = (chirp_idx - config['num_chirps']//2) * (
                3e8 / (2 * config['center_freq'] * config['num_chirps'] * config['chirp_duration'])
            )
            
            if abs(velocity) > 0.5:  # Velocity threshold
                detections.append([range_val, velocity])
        
        # Cluster detections
        if detections:
            clustering = DBSCAN(eps=0.5, min_samples=2).fit(detections)
            return clustering.labels_, np.array(detections)
        return [], []
    
    def process(self):
        """Main processing loop"""
        self.connect()
        frame_count = 0
        
        try:
            while True:
                start_time = time.time()
                
                # Receive frame
                header, frame_data = self.receive_frame()
                
                # Process frame
                labels, detections = self.detect_targets(
                    frame_data, 
                    header['config']
                )
                
                # Output results
                frame_count += 1
                elapsed = (time.time() - start_time) * 1000
                print(f"\nFrame {frame_count} [{header['timestamp']}]")
                print(f"Processing time: {elapsed:.2f} ms")
                print(f"Detected {len(detections)} points in {len(set(labels))} clusters")
                
                # Show cluster details
                for label in set(labels):
                    if label == -1:
                        continue
                    cluster_points = detections[labels == label]
                    centroid = np.mean(cluster_points, axis=0)
                    print(f"  Cluster {label}: {len(cluster_points)} points")
                    print(f"  Center: Range={centroid[0]:.2f}m, Velocity={centroid[1]:.2f}m/s")
                
                # Maintain processing rate
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("\nStopping radar processing")
        finally:
            self.sock.close()

if __name__ == "__main__":
    processor = RadarProcessor()
    processor.process()