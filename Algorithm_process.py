import numpy as np
import matplotlib.pyplot as plt
from scipy.fft import fft, fftfreq, fftshift
from scipy.signal import stft, istft
from sklearn.cluster import DBSCAN
import time
import serial
import serial.tools.list_ports
import json
import os
from enum import Enum

# Constants based on paper specifications
c = 3e8  # Speed of light

class RadarConfig:
    def __init__(self):
        # TI IWR6843 specifications (Section 3.1.1)
        self.center_freq = 62e9  # 60-64 GHz
        self.bandwidth = 4e9     # 4 GHz bandwidth
        self.chirp_duration = 50e-6  # 50 μs
        self.num_samples = 256   # Samples per chirp
        self.num_chirps = 64     # Chirps per frame
        self.num_rx = 3          # Number of RX antennas
        self.fs = 10e6           # Sampling rate (10 MSPS)
        
        # Derived parameters
        self.lambda_ = c / self.center_freq
        self.range_resolution = c / (2 * self.bandwidth)
        self.max_range = (c * self.fs) / (4 * self.bandwidth)
        self.velocity_resolution = self.lambda_ / (2 * self.num_chirps * self.chirp_duration)
        self.max_velocity = self.lambda_ / (4 * self.chirp_duration)
        self.d_antenna = self.lambda_ / 2  # Antenna spacing

class RadarProcessor:
    def __init__(self, config):
        self.config = config
        self.background = None
        self.frame_count = 0
        
        # Initialize angle estimation parameters
        self.angle_bins = 64
        self.angle_range = np.arcsin(np.linspace(-1, 1, self.angle_bins))
        
        # Clutter suppression parameters (Section 3.2.1)
        self.clutter_alpha = 0.05  # Learning rate for background model

    def range_fft(self, adc_data):
        """Perform range FFT with windowing (Section 3.2.1)"""
        window = np.hamming(self.config.num_samples)
        windowed = adc_data * window
        return fft(windowed, axis=2)
    
    def doppler_processing(self, range_fft_data):
        """Perform Doppler processing with windowing (Section 3.2.1)"""
        window = np.hamming(self.config.num_chirps)
        windowed = range_fft_data * window[:, np.newaxis, np.newaxis]
        return fftshift(fft(windowed, axis=0), axes=0)
    
    def clutter_suppression(self, doppler_data):
        """Adaptive clutter suppression (Section 3.2.1 and 5.2.3.1)"""
        if self.background is None:
            self.background = np.mean(doppler_data, axis=0)
            return np.zeros_like(doppler_data)
        
        foreground = doppler_data - self.background
        # Adaptive background update
        self.background = (1 - self.clutter_alpha) * self.background + self.clutter_alpha * doppler_data
        return foreground
    
    def detect_targets(self, processed_data):
        """CFAR detection with dynamic thresholding (Section 3.2.2)"""
        power = np.abs(processed_data)**2
        threshold = np.percentile(power, 95) * 0.5  # Dynamic threshold
        
        # Find peaks above threshold
        peaks = np.where(power > threshold)
        return list(zip(peaks[0], peaks[1], peaks[2]))  # (doppler, rx, range)
    
    def estimate_aoa(self, doppler_data, doppler_bin, range_bin):
        """Estimate Angle of Arrival using phase differences (Section 2.1)"""
        # Extract phase information across antennas
        phases = np.angle(doppler_data[doppler_bin, :, range_bin])
        
        # Calculate phase differences
        phase_diffs = np.diff(phases)
        
        # Estimate angle using phase differences
        sin_theta = (phase_diffs * self.config.lambda_) / (2 * np.pi * self.config.d_antenna)
        sin_theta = np.clip(sin_theta, -1, 1)
        angles = np.arcsin(sin_theta)
        return np.mean(angles)
    
    def process_frame(self, frame):
        """Full processing pipeline for one radar frame (Section 3.2)"""
        # Reshape to (chirps, rx, samples)
        data = frame.reshape(self.config.num_chirps, self.config.num_rx, self.config.num_samples)
        
        # Signal processing pipeline
        range_fft = self.range_fft(data)
        doppler_fft = self.doppler_processing(range_fft)
        clutter_suppressed = self.clutter_suppression(doppler_fft)
        
        # Target detection
        detections = self.detect_targets(clutter_suppressed)
        
        # Process detections
        targets = []
        for doppler_bin, rx_bin, range_bin in detections:
            # Convert bins to physical units
            range_val = range_bin * self.config.range_resolution
            velocity = (doppler_bin - self.config.num_chirps//2) * self.config.velocity_resolution
            
            # Only process significant velocities
            if abs(velocity) < self.config.doppler_threshold:
                continue
                
            # Estimate angle
            angle = self.estimate_aoa(clutter_suppressed, doppler_bin, range_bin)
            
            targets.append({
                'range': range_val,
                'velocity': velocity,
                'angle': np.degrees(angle),
                'doppler_bin': doppler_bin,
                'range_bin': range_bin
            })
        
        # Cluster targets (Section 5.2.3)
        clustered_targets = self.cluster_targets(targets)
        self.frame_count += 1
        return clustered_targets
    
    def cluster_targets(self, targets):
        """Cluster detections using DBSCAN (Section 5.2.3)"""
        if not targets:
            return []
        
        # Prepare feature matrix (range, angle, velocity)
        features = np.array([
            [t['range'], t['angle'], t['velocity']] 
            for t in targets
        ])
        
        # Normalize features
        ranges = features[:, 0] / self.config.max_range
        angles = features[:, 1] / 180  # Normalize to ±1
        velocities = features[:, 2] / self.config.max_velocity
        
        norm_features = np.column_stack((ranges, angles, velocities))
        
        # Apply DBSCAN clustering
        clustering = DBSCAN(eps=0.1, min_samples=1).fit(norm_features)
        labels = clustering.labels_
        
        # Group targets by cluster
        clusters = []
        for label in set(labels):
            if label == -1:  # Skip noise
                continue
                
            cluster_points = [t for t, l in zip(targets, labels) if l == label]
            
            # Calculate cluster centroid
            centroid = {
                'range': np.mean([t['range'] for t in cluster_points]),
                'velocity': np.mean([t['velocity'] for t in cluster_points]),
                'angle': np.mean([t['angle'] for t in cluster_points]),
                'size': len(cluster_points)
            }
            clusters.append(centroid)
        
        return clusters

class RadarDataReceiver:
    def __init__(self, config, port=None, baudrate=921600):
        self.config = config
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        
        if port:
            self.connect()
    
    def connect(self):
        """Connect to radar hardware"""
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"Connected to radar at {self.port}")
            return True
        except serial.SerialException as e:
            print(f"Connection failed: {e}")
            self.ser = None
            return False
    
    def find_radar(self):
        """Automatically detect radar port"""
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if 'ACM' in port.device or 'USB' in port.description:
                self.port = port.device
                if self.connect():
                    return True
        return False
    
    def read_frame(self):
        """Read a complete frame from radar"""
        frame_size = self.config.num_chirps * self.config.num_rx * self.config.num_samples * 4
        if self.ser is None:
            return self.simulate_frame()
        
        data = self.ser.read(frame_size)
        if len(data) < frame_size:
            print(f"Incomplete frame: {len(data)}/{frame_size} bytes")
            return None
        
        # Convert to complex numbers (I+jQ)
        iq = np.frombuffer(data, dtype=np.int16).astype(np.float32).view(np.complex64)
        return iq
    
    def simulate_frame(self):
        """Generate simulated radar data with moving targets"""
        frame_size = self.config.num_chirps * self.config.num_rx * self.config.num_samples
        noise = 0.1 * (np.random.randn(frame_size) + 1j * np.random.randn(frame_size))
        
        # Add 1-3 moving targets
        for _ in range(np.random.randint(1, 4)):
            range_val = np.random.uniform(1, self.config.max_range)
            velocity = np.random.uniform(-5, 5)
            angle = np.radians(np.random.uniform(-60, 60))
            
            # Convert to bins
            range_bin = int(range_val / self.config.range_resolution) % self.config.num_samples
            doppler_bin = int(self.config.num_chirps//2 + 
                             velocity / self.config.velocity_resolution) % self.config.num_chirps
            
            # Add target signature
            for rx in range(self.config.num_rx):
                # Calculate phase shift due to angle
                phase_shift = 2 * np.pi * rx * self.config.d_antenna * np.sin(angle) / self.config.lambda_
                
                # Create target signature
                idx = (doppler_bin * self.config.num_rx + rx) * self.config.num_samples + range_bin
                if idx < frame_size:
                    noise[idx] += 10 * np.exp(1j * phase_shift)
        
        return noise

class Visualization:
    @staticmethod
    def plot_range_doppler(data, config):
        """Plot range-Doppler map (Section 5.1.2)"""
        plt.figure(figsize=(12, 8))
        plt.imshow(20*np.log10(np.abs(data[:, 0, :])), 
                  aspect='auto',
                  extent=[0, config.max_range, 
                          -config.max_velocity, config.max_velocity])
        plt.colorbar(label='Power (dB)')
        plt.xlabel('Range (m)')
        plt.ylabel('Velocity (m/s)')
        plt.title('Range-Doppler Map')
        plt.tight_layout()
        plt.show(block=False)
    
    @staticmethod
    def plot_detections(detections):
        """Plot detected targets in polar coordinates"""
        if not detections:
            return
        
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='polar')
        
        for target in detections:
            r = target['range']
            theta = np.radians(target['angle'])
            size = 50 + target.get('size', 1) * 20
            
            ax.scatter(theta, r, s=size, c='red', alpha=0.7)
            ax.text(theta, r, f"{target['velocity']:.1f}m/s", 
                   fontsize=9, ha='center', va='bottom')
        
        ax.set_theta_zero_location('N')
        ax.set_theta_direction(-1)
        ax.set_rmax(20)  # Limit to 20m range
        ax.grid(True)
        ax.set_title('Detected Targets (Range vs Angle)')
        plt.tight_layout()
        plt.show(block=False)
    
    @staticmethod
    def update_plots(range_doppler, detections, config):
        plt.close('all')
        Visualization.plot_range_doppler(range_doppler, config)
        Visualization.plot_detections(detections)
        plt.pause(0.1)

def main():
    # Initialize configuration
    config = RadarConfig()
    config.doppler_threshold = 0.5  # Velocity threshold (m/s)
    
    # Initialize data receiver
    receiver = RadarDataReceiver(config)
    
    # Try to find and connect to radar
    if not receiver.port:
        print("Searching for radar...")
        if not receiver.find_radar():
            print("No radar found. Running in simulation mode.")
    
    # Initialize processor
    processor = RadarProcessor(config)
    
    print("\nmmWave Radar Motion Detection System")
    print(f"Mode: {'HARDWARE' if receiver.ser else 'SIMULATION'}")
    print(f"Range Resolution: {config.range_resolution*100:.2f} cm")
    print(f"Velocity Resolution: {config.velocity_resolution:.2f} m/s")
    print(f"Max Range: {config.max_range:.1f} m")
    print(f"Max Velocity: {config.max_velocity:.1f} m/s\n")
    
    try:
        plt.ion()  # Interactive mode for live updating
        while True:
            start_time = time.time()
            
            # Get radar data
            frame = receiver.read_frame()
            if frame is None:
                time.sleep(0.1)
                continue
            
            # Process frame
            detected_objects = processor.process_frame(frame)
            processing_time = (time.time() - start_time) * 1000
            
            # Output results
            print(f"\nFrame {processor.frame_count}:")
            print(f"Processing time: {processing_time:.2f} ms")
            print(f"Detected {len(detected_objects)} objects:")
            
            for i, obj in enumerate(detected_objects):
                print(f"  Object {i+1}:")
                print(f"    Range: {obj['range']:.2f}m")
                print(f"    Velocity: {obj['velocity']:.2f}m/s")
                print(f"    Angle: {obj['angle']:.1f}°")
                if 'size' in obj:
                    print(f"    Size: {obj['size']} points")
            
            # Visualization (update every 5 frames)
            if processor.frame_count % 5 == 0:
                # For visualization, we need the range-Doppler data
                # This would normally be stored in the processor
                # For simplicity, we'll recreate it
                data = frame.reshape(config.num_chirps, config.num_rx, config.num_samples)
                range_fft = processor.range_fft(data)
                doppler_fft = processor.doppler_processing(range_fft)
                clutter_suppressed = processor.clutter_suppression(doppler_fft)
                
                Visualization.update_plots(clutter_suppressed, detected_objects, config)
            
            time.sleep(0.1)  # Control frame rate
    
    except KeyboardInterrupt:
        print("\nStopping radar processing")
        if receiver.ser:
            receiver.ser.close()
        plt.ioff()
        plt.close('all')

if __name__ == "__main__":
    main()