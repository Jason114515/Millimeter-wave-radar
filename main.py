import multiprocessing
import subprocess
import time
import signal
import sys

def run_data_collection():
    """Run the radar data collection module"""
    subprocess.run(["python", "Data_collection.py"])

def run_data_processing():
    """Run the radar data processing module"""
    # Add delay to ensure receiver is ready
    time.sleep(2)
    subprocess.run(["python", "Data_processing.py"])

def run_web_ui():
    """Run the web UI module"""
    subprocess.run(["python", "web_UI.py"])

def signal_handler(sig, frame):
    """Handle Ctrl+C signal to terminate all processes"""
    print("\nTerminating all processes...")
    for p in processes:
        p.terminate()
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create process list
    processes = []
    
    # Start data collection process
    p1 = multiprocessing.Process(target=run_data_collection)
    p1.start()
    processes.append(p1)
    print("Started radar data collection")
    
    # Start data processing process
    p2 = multiprocessing.Process(target=run_data_processing)
    p2.start()
    processes.append(p2)
    print("Started radar data processing")
    
    # Start web UI process
    p3 = multiprocessing.Process(target=run_web_ui)
    p3.start()
    processes.append(p3)
    print("Started web UI at http://localhost:5000")
    
    # Keep main process alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)