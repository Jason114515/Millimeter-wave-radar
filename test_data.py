import numpy as np
import time
import threading
import requests
import json
from flask import Flask, render_template_string
from datetime import datetime
from waitress import serve


# Radar configuration parameters (matches your system specs)
RADAR_CONFIG = {
    'center_freq': 62e9,
    'bandwidth': 4e9,
    'chirp_duration': 50e-6,
    'num_samples': 256,
    'num_chirps': 64,
    'num_rx': 3,
    'fs': 10e6
}

# Web UI Server Setup
app = Flask(__name__)

# In-memory data store for web UI
system_status = {
    'operation': 'running',
    'last_update': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    'targets_detected': 0,
    'system_health': 'good',
    'alerts': []
}

performance_metrics = {
    'original_processing_time': 142,
    'optimized_processing_time': 85,
    'accuracy_improvement': 15.7,
    'false_positive_reduction': 32.5
}

targets = {}
next_target_id = 1

# Web UI Route
@app.route('/')
def dashboard():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>mmWave Radar System</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            .dashboard { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; }
            .header { background: #2c3e50; color: white; padding: 20px; text-align: center; }
            .metrics { display: flex; justify-content: space-between; margin: 20px 0; }
            .metric-card { background: #f8f9fa; border-radius: 8px; padding: 20px; text-align: center; flex: 1; margin: 0 10px; }
            .metric-value { font-size: 2rem; font-weight: bold; }
            .visualization { display: flex; margin: 20px 0; }
            .radar-display, .data-display { flex: 1; padding: 20px; background: #f8f9fa; border-radius: 8px; margin: 0 10px; }
            canvas { width: 100% !important; height: 300px !important; }
        </style>
    </head>
    <body>
        <div class="dashboard">
            <div class="header">
                <h1>mmWave Radar Motion Detection System</h1>
                <p>Real-time monitoring and analysis</p>
            </div>
            
            <div class="metrics">
                <div class="metric-card">
                    <h3>Targets Detected</h3>
                    <div class="metric-value" id="target-count">0</div>
                </div>
                <div class="metric-card">
                    <h3>Processing Time</h3>
                    <div class="metric-value" id="processing-time">0 ms</div>
                </div>
                <div class="metric-card">
                    <h3>System Health</h3>
                    <div class="metric-value" id="system-health">Good</div>
                </div>
            </div>
            
            <div class="visualization">
                <div class="radar-display">
                    <h3>Radar Visualization</h3>
                    <canvas id="radarCanvas"></canvas>
                </div>
                <div class="data-display">
                    <h3>Target Information</h3>
                    <div id="target-info"></div>
                </div>
            </div>
        </div>
        
        <script>
            // Radar visualization
            const radarCtx = document.getElementById('radarCanvas').getContext('2d');
            let radarChart;
            
            // Initialize radar display
            function initRadar() {
                radarChart = new Chart(radarCtx, {
                    type: 'radar',
                    data: {
                        labels: ['Range', 'Velocity', 'Angle', 'Stability', 'Size'],
                        datasets: [{
                            label: 'Target Signature',
                            data: [0, 0, 0, 0, 0],
                            fill: true,
                            backgroundColor: 'rgba(54, 162, 235, 0.2)',
                            borderColor: 'rgb(54, 162, 235)',
                            pointBackgroundColor: 'rgb(54, 162, 235)',
                            pointBorderColor: '#fff',
                            pointHoverBackgroundColor: '#fff',
                            pointHoverBorderColor: 'rgb(54, 162, 235)'
                        }]
                    },
                    options: {
                        scales: {
                            r: {
                                angleLines: { display: true },
                                suggestedMin: 0,
                                suggestedMax: 10
                            }
                        }
                    }
                });
            }
            
            // Update dashboard with new data
            function updateDashboard(data) {
                // Update metrics
                document.getElementById('target-count').textContent = data.target_count;
                document.getElementById('processing-time').textContent = data.processing_time.toFixed(2) + ' ms';
                document.getElementById('system-health').textContent = data.system_health;
                
                // Update radar visualization
                if (radarChart) {
                    radarChart.data.datasets[0].data = [
                        data.avg_range || 0,
                        Math.abs(data.avg_velocity) || 0,
                        data.angle || 0,
                        data.stability || 5,
                        data.size || 3
                    ];
                    radarChart.update();
                }
                
                // Update target information
                let targetHtml = '<ul>';
                if (data.targets && data.targets.length > 0) {
                    data.targets.forEach(target => {
                        targetHtml += `
                            <li>
                                <strong>Target #${target.id}</strong><br>
                                Type: ${target.type}<br>
                                Range: ${target.range.toFixed(2)} m<br>
                                Velocity: ${target.velocity.toFixed(2)} m/s<br>
                                Angle: ${target.angle.toFixed(1)}°
                            </li>
                        `;
                    });
                } else {
                    targetHtml += '<li>No targets detected</li>';
                }
                targetHtml += '</ul>';
                document.getElementById('target-info').innerHTML = targetHtml;
            }
            
            // Initialize radar when page loads
            window.onload = initRadar;
            
            // Periodically fetch new data
            setInterval(() => {
                fetch('/radar_data')
                    .then(response => response.json())
                    .then(data => updateDashboard(data));
            }, 1000);
        </script>
    </body>
    </html>
    """)

# API endpoint for radar data
@app.route('/radar_data')
def radar_data():
    return {
        'target_count': system_status['targets_detected'],
        'processing_time': performance_metrics['optimized_processing_time'],
        'system_health': system_status['system_health'],
        'avg_range': 5.2 if targets else 0,
        'avg_velocity': 1.8 if targets else 0,
        'angle': 30 if targets else 0,
        'stability': 7.5 if targets else 0,
        'size': 4 if targets else 0,
        'targets': [
            {
                'id': t['id'],
                'type': t['type'],
                'range': t['range'],
                'velocity': t['velocity'],
                'angle': t['angle']
            } for t in targets.values()
        ]
    }

# Radar Data Simulator
def simulate_radar_data():
    """Generate simulated radar data frames"""
    global next_target_id, targets, system_status
    
    while True:
        # Randomly determine if we have targets in this frame
        has_targets = np.random.random() > 0.3
        
        if has_targets:
            # Create 1-4 targets
            num_targets = np.random.randint(1, 5)
            targets = {}
            
            for i in range(num_targets):
                target_id = next_target_id
                next_target_id += 1
                
                # Target characteristics
                target_type = np.random.choice(['human', 'vehicle', 'animal'])
                range_val = np.random.uniform(1.0, 20.0)
                velocity = np.random.uniform(-5.0, 5.0)
                angle = np.random.uniform(0, 360)
                
                targets[target_id] = {
                    'id': target_id,
                    'type': target_type,
                    'range': range_val,
                    'velocity': velocity,
                    'angle': angle,
                    'first_detected': datetime.now().isoformat()
                }
            
            system_status['targets_detected'] = num_targets
        else:
            targets = {}
            system_status['targets_detected'] = 0
        
        # Update system status
        system_status['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Randomly change system health occasionally
        if np.random.random() < 0.05:
            system_status['system_health'] = np.random.choice(['good', 'warning', 'critical'])
        
        # Simulate processing time (50-150ms)
        processing_time = np.random.uniform(0.05, 0.15)
        performance_metrics['optimized_processing_time'] = processing_time
        performance_metrics['accuracy_improvement'] = np.clip(
            performance_metrics['accuracy_improvement'] + np.random.uniform(-0.5, 0.5), 
            10, 25
        )
        
        time.sleep(1)  # Simulate 1 FPS

# Data Processing Simulation
def process_radar_data():
    """Simulate the data processing pipeline"""
    # This would normally contain your radar signal processing algorithms
    # For simulation, we'll just pass through the data
    while True:
        # In a real system, this would receive data from Data_collection.py
        # and process it using the algorithms from Data_processing.py
        time.sleep(0.3)

# Main function
def main():
    # Start web server in a separate thread
    server_thread = threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False, threaded=True)
    )
    server_thread.daemon = True
    server_thread.start()
    
    # Start radar data simulator
    radar_sim_thread = threading.Thread(target=simulate_radar_data)
    radar_sim_thread.daemon = True
    radar_sim_thread.start()
    
    # Start data processing simulation
    processing_thread = threading.Thread(target=process_radar_data)
    processing_thread.daemon = True
    processing_thread.start()
    
    print("System running. Open http://localhost:5000 to view the dashboard")
    print("Press Ctrl+C to exit")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting...")

if __name__ == "__main__":
    main()