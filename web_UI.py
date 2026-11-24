#!/usr/bin/env python3
"""
Millimeter-Wave Radar Motion Detection System - Web_UI
Based on: "Motion detection via mmWave radars" by XIE Wenbo
Department of Computer Science, City University of Hong Kong
"""

from flask import Flask, render_template, request, jsonify, session, send_file
import time
import threading
import queue
import json
import os
import numpy as np
from datetime import datetime, timedelta
import random
from fpdf import FPDF
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

app = Flask(__name__)
app.secret_key = 'radar_secret_key'
data_queue = queue.Queue()

# ==========================================
# System Control
# ==========================================

class SystemControl:
    def __init__(self):
        self.running = True
        self.reboot_requested = False
        self.report_history = []  # Track generated reports

system_control = SystemControl()

# ==========================================
# System Configuration and State
# ==========================================

class RadarTarget:
    """Represents a detected target"""
    def __init__(self, target_id):
        self.id = target_id
        self.type = random.choice(['human', 'vehicle', 'animal', 'unknown'])
        self.first_detected = datetime.now()
        self.last_detected = datetime.now()
        self.max_speed = round(random.uniform(0.5, 10.0), 1)
        self.avg_range = round(random.uniform(1.0, 30.0), 1)
        self.status = 'active'
        self.history = []
        
    def update_position(self):
        """Update target position and status"""
        self.last_detected = datetime.now()
        duration = (self.last_detected - self.first_detected).seconds
        if duration > 30:  # Mark as inactive after 30 seconds
            self.status = 'inactive'
        
        # Add position to history
        position = {
            'x': round(random.uniform(-10, 10), 1),
            'y': round(random.uniform(0, 20), 1),
            'timestamp': self.last_detected.strftime("%H:%M:%S")
        }
        self.history.append(position)
        if len(self.history) > 20:  # Limit history size
            self.history.pop(0)

class RadarSystem:
    """Represents the mmWave radar system state and configuration"""
    def __init__(self):
        self.config = {
            'range_resolution': 0.05,  # meters
            'velocity_error': 0.1,     # m/s
            'angular_resolution': 1.5, # degrees
            'detection_threshold': 2.5,
            'alert_email': 'admin@example.com',
            'alert_sms': '+1234567890',
            'sensitivity': 'medium'
        }
        self.status = {
            'operation': 'running',
            'last_update': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'targets_detected': 0,
            'system_health': 'good',
            'alerts': []
        }
        self.performance = {
            'original_processing_time': 0.42,
            'optimized_processing_time': 0.12,
            'accuracy_improvement': 15.7,
            'false_positive_reduction': 32.5
        }
        self.targets = {}
        self.next_target_id = 1
        self.alert_counters = {
            'motion': 0,
            'system': 0
        }
        self.performance_history = []  # Track performance over time
    
    def add_target(self):
        """Add a new detected target"""
        target_id = self.next_target_id
        self.next_target_id += 1
        target = RadarTarget(target_id)
        self.targets[target_id] = target
        self.status['targets_detected'] = len([t for t in self.targets.values() if t.status == 'active'])
        return target
    
    def update_targets(self):
        """Update all active targets"""
        # Randomly add new targets
        if random.random() < 0.3:  # 30% chance to add a new target
            self.add_target()
        
        # Update existing targets
        for target in list(self.targets.values()):
            if target.status == 'active':
                target.update_position()
    
    def add_alert(self, alert_type, target=None):
        """Add a new system alert"""
        alert = {
            'id': len(self.status['alerts']) + 1,
            'type': alert_type,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'acknowledged': False,
            'target': target
        }
        self.status['alerts'].append(alert)
        
        # Update alert counters
        if 'motion' in alert_type.lower():
            self.alert_counters['motion'] += 1
        else:
            self.alert_counters['system'] += 1
            
        return alert
    
    def acknowledge_alert(self, alert_id):
        """Mark an alert as acknowledged"""
        for alert in self.status['alerts']:
            if alert['id'] == alert_id:
                alert['acknowledged'] = True
                return True
        return False
    
    def get_system_status(self):
        """Return current system status"""
        self.status['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return self.status
    
    def update_performance(self):
        """Update performance metrics with slight variations"""
        self.performance = {
        'original_processing_time': max(0.3, min(0.5, 
            self.performance['original_processing_time'] + random.uniform(-0.01, 0.01))),
        'optimized_processing_time': max(0.1, min(0.2, 
            self.performance['optimized_processing_time'] + random.uniform(-0.005, 0.005))),
        'accuracy_improvement': max(10, min(25, 
            self.performance['accuracy_improvement'] + random.uniform(-0.1, 0.1))),
        'false_positive_reduction': max(25, min(40, 
            self.performance['false_positive_reduction'] + random.uniform(-0.1, 0.1)))}
                # Add to history
        self.performance_history.append({
            'timestamp': datetime.now(),
            'metrics': dict(self.performance)
        })
        # Keep only last 100 entries
        if len(self.performance_history) > 100:
            self.performance_history.pop(0)


# Initialize system
radar_system = RadarSystem()

# ==========================================
# Background Simulation Thread
# ==========================================

def simulate_radar_data():
    """Background thread to simulate radar data updates"""
    global radar_system
    while True:
        # Update system status
        radar_system.status['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Check system state
        if not system_control.running:
            time.sleep(1)
            continue
            
        if system_control.reboot_requested:
            # Reset system state
            radar_system = RadarSystem()
            system_control.reboot_requested = False
        
        # Randomly change system health
        if random.random() < 0.02:  # 2% chance to change health
            radar_system.status['system_health'] = random.choice(['good', 'warning', 'critical'])
        
        # Update targets
        radar_system.update_targets()
        
        # Randomly generate alerts
        if random.random() < 0.1:  # 10% chance to generate alert
            alert_types = ['Motion Detected', 'System Warning', 'Critical Error']
            alert_type = random.choice(alert_types)
            
            # Select a random active target for motion alerts
            target = None
            active_targets = [t for t in radar_system.targets.values() if t.status == 'active']
            if alert_type == 'Motion Detected' and active_targets:
                target = random.choice(active_targets)
            
            radar_system.add_alert(alert_type, target)
        
        # Update performance metrics
        radar_system.update_performance()
        
        # Put update in queue for websocket-like behavior
        data_queue.put({
            'status': radar_system.status,
            'performance': radar_system.performance,
            'target_count': radar_system.status['targets_detected']
        })
        
        time.sleep(2)  # Update every 2 seconds

# Start simulation thread
sim_thread = threading.Thread(target=simulate_radar_data, daemon=True)
sim_thread.start()

# ==========================================
# Web Application Routes
# ==========================================

@app.route('/')
def dashboard():
    """Main dashboard page"""
    system_status = radar_system.get_system_status()
    # Calculate progress bar values
    range_percentage = min(100, (radar_system.config['range_resolution'] * 100 / 0.2) * 100)
    velocity_percentage = min(100, (1 - radar_system.config['velocity_error'] / 1.0) * 100)
    angular_percentage = min(100, (5 - radar_system.config['angular_resolution']) / 4 * 100)

    """Main dashboard page"""
    if not system_control.running:
        return render_template('shutdown.html')
    
    return render_template('dashboard.html', 
                           config=radar_system.config,
                           status=system_status,
                           performance=radar_system.performance,
                           range_percentage=range_percentage,
                           velocity_percentage=velocity_percentage,
                           angular_percentage=angular_percentage)

@app.route('/config', methods=['GET', 'POST'])
def configuration():
    """System configuration page"""
    if request.method == 'POST':
        # Update configuration from form
        radar_system.config['range_resolution'] = float(request.form['range_res'])
        radar_system.config['velocity_error'] = float(request.form['vel_error'])
        radar_system.config['angular_resolution'] = float(request.form['ang_res'])
        radar_system.config['detection_threshold'] = float(request.form['threshold'])
        radar_system.config['alert_email'] = request.form['alert_email']
        radar_system.config['alert_sms'] = request.form['alert_sms']
        radar_system.config['sensitivity'] = request.form['sensitivity']
        return jsonify(success=True)
    return render_template('config.html', config=radar_system.config)

@app.route('/alerts')
def alert_management():
    """Alert management page"""
    system_status = radar_system.get_system_status()
    return render_template('alerts.html', alerts=system_status['alerts'])

@app.route('/performance')
def performance_comparison():
    """Algorithm performance comparison page"""
    return render_template('performance.html', 
                           performance=radar_system.performance,
                           config=radar_system.config)


@app.route('/targets')
def target_tracking():
    """Target tracking history page - supports JSON response"""
    if request.args.get('json'):
        # Return targets as JSON for AJAX requests
        target_list = []
        for target in radar_system.targets.values():
            target_list.append({
                'id': target.id,
                'type': target.type,
                'history': target.history,
                'status': target.status,
                'first_detected': target.first_detected.strftime("%Y-%m-%d %H:%M:%S"),
                'last_detected': target.last_detected.strftime("%Y-%m-%d %H:%M:%S"),
                'duration': str(timedelta(seconds=(target.last_detected - target.first_detected).seconds)).split(".")[0],
                'max_speed': f"{target.max_speed} m/s",
                'avg_range': f"{target.avg_range} m"
            })
        return jsonify(target_list)
    
    # Prepare target data for display (original HTML rendering)
    target_list = []
    for target in radar_system.targets.values():
        duration = (target.last_detected - target.first_detected)
        target_list.append({
            'id': target.id,
            'type': target.type,
            'first_detected': target.first_detected.strftime("%Y-%m-%d %H:%M:%S"),
            'last_detected': target.last_detected.strftime("%Y-%m-%d %H:%M:%S"),
            'duration': str(timedelta(seconds=duration.seconds)).split(".")[0],
            'max_speed': f"{target.max_speed} m/s",
            'avg_range': f"{target.avg_range} m",
            'status': target.status,
            'history': target.history
        })
    
    # Sort by last detected (newest first)
    target_list.sort(key=lambda x: x['last_detected'], reverse=True)
    
    if request.args.get('partial'):
        # Return just the table body for AJAX updates
        return render_template('target_table.html', targets=target_list)
    
    return render_template('targets.html', targets=target_list)

@app.route('/acknowledge_alert/<int:alert_id>', methods=['POST'])
def acknowledge_alert(alert_id):
    """Acknowledge an alert"""
    if radar_system.acknowledge_alert(alert_id):
        return jsonify(success=True)
    return jsonify(success=False, error="Alert not found"), 404

@app.route('/system_status')
def get_system_status():
    """API endpoint for system status"""
    return jsonify(radar_system.get_system_status())

@app.route('/target_data')
def get_target_data():
    """API endpoint for target data - counts all targets by type"""
    # Count each target type from all targets
    human_count = len([t for t in radar_system.targets.values() if t.type == 'human'])
    vehicle_count = len([t for t in radar_system.targets.values() if t.type == 'vehicle'])
    animal_count = len([t for t in radar_system.targets.values() if t.type == 'animal'])
    other_count = len([t for t in radar_system.targets.values() if t.type == 'unknown'])
    
    return jsonify({
        'human_targets': human_count,
        'vehicle_targets': vehicle_count,
        'animal_targets': animal_count,
        'other_targets': other_count,
        'total_targets': len(radar_system.targets)
    })

@app.route('/performance_data')
def get_performance_data():
    """API endpoint for performance data"""
    return jsonify(radar_system.performance)

@app.route('/alert_counts')
def get_alert_counts():
    """API endpoint for alert counts"""
    active_alerts = [a for a in radar_system.status['alerts'] if not a['acknowledged']]
    return jsonify({
        'total_active': len(active_alerts),
        'motion_alerts': len([a for a in active_alerts if 'Motion' in a['type']]),
        'system_alerts': len([a for a in active_alerts if 'Motion' not in a['type']]),
        'acknowledged': len(radar_system.status['alerts']) - len(active_alerts)
    })

# ==========================================
# System Control Routes
# ==========================================

@app.route('/reboot_system', methods=['POST'])
def reboot_system():
    """Reboot the system and reset all state"""
    system_control.reboot_requested = True
    return jsonify(success=True, message="System rebooting...")

@app.route('/shutdown_system', methods=['POST'])
def shutdown_system():
    """Shutdown the system"""
    system_control.running = False
    return jsonify(success=True, message="System shutting down...")

# ==========================================
# New Routes for Report Generation
# ==========================================

@app.route('/export_performance_report')
def export_performance_report():
    """Generate and download a PDF performance report"""
    # Create a PDF buffer
    buffer = io.BytesIO()
    
    # Create PDF
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Set up PDF content
    p.setFont("Helvetica-Bold", 18)
    p.drawString(100, height - 100, "mmWave Radar Performance Report")
    
    # Report metadata
    p.setFont("Helvetica", 12)
    p.drawString(100, height - 140, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    p.drawString(100, height - 160, f"System Health: {radar_system.status['system_health'].capitalize()}")
    
    # Performance metrics
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, height - 200, "Algorithm Performance Metrics")
    
    p.setFont("Helvetica", 12)
    y = height - 230
    for metric, value in radar_system.performance.items():
        label = metric.replace('_', ' ').title()
        p.drawString(120, y, f"{label}: {value:.2f}")
        y -= 25
    
    # Configuration details
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, y - 40, "System Configuration")
    
    p.setFont("Helvetica", 12)
    y -= 70
    for key, value in radar_system.config.items():
        label = key.replace('_', ' ').title()
        p.drawString(120, y, f"{label}: {value}")
        y -= 25
    
    # Save PDF
    p.showPage()
    p.save()
    
    # Create response
    buffer.seek(0)
    filename = f"radar_performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )


# ==========================================
# Rendering Setup
# ==========================================

# Create templates directory
os.makedirs('templates', exist_ok=True)

# Dashboard
with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>mmWave Radar - Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        .card-header { font-weight: 600; }
        .status-badge { font-size: 0.85rem; }
        .metric-card { transition: transform 0.2s; }
        .metric-card:hover { transform: translateY(-5px); }
        .alert-badge { position: absolute; top: -8px; right: -8px; }
        .system-health { font-size: 1.2rem; font-weight: 500; }
        .health-good { color: #28a745; }
        .health-warning { color: #ffc107; }
        .health-critical { color: #dc3545; }
        .nav-tabs .nav-link.active { font-weight: 600; }
        .performance-bar { height: 25px; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="/">
                <i class="fa-solid fa-radar"></i> mmWave Radar System
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link active" href="/">
                            <i class="fa-solid fa-gauge"></i> Dashboard
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/config">
                            <i class="fa-solid fa-sliders"></i> Configuration
                        </a>
                    </li>
                    <li class="nav-item position-relative">
                        <a class="nav-link" href="/alerts">
                            <i class="fa-solid fa-bell"></i> Alerts
                            <span class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger" id="alertCountBadge">
                                {{ status.alerts|rejectattr('acknowledged')|list|length }}
                            </span>
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/performance">
                            <i class="fa-solid fa-chart-line"></i> Performance
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/targets">
                            <i class="fa-solid fa-bullseye"></i> Targets
                        </a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container-fluid mt-4">
        <div class="row">
            <!-- Main Content -->
            <div class="col-lg-9">
                <div class="card mb-4">
                    <div class="card-header bg-primary text-white">
                        <i class="fa-solid fa-radar"></i> Real-time Detection Overview
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-8">
                                <div class="position-relative" style="height: 300px; background: #f8f9fa; border-radius: 5px;">
                                    <canvas id="detectionCanvas"></canvas>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="card mb-3">
                                    <div class="card-body">
                                        <div class="d-flex justify-content-between align-items-center">
                                            <div>
                                                <h5 class="card-title">System Health</h5>
                                                <span class="system-health health-{{ status.system_health }}">{{ status.system_health|capitalize }}</span>
                                            </div>
                                            <i class="fa-solid fa-heart-pulse fa-2x 
                                                {% if status.system_health == 'good' %}text-success{% elif status.system_health == 'warning' %}text-warning{% else %}text-danger{% endif %}"></i>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="card mb-3">
                                    <div class="card-body">
                                        <div class="d-flex justify-content-between align-items-center">
                                            <div>
                                                <h5 class="card-title">Operation Status</h5>
                                                <span class="text-primary" id="operationStatus">{{ status.operation|capitalize }}</span>
                                            </div>
                                            <i class="fa-solid fa-power-off fa-2x text-primary"></i>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="card">
                                    <div class="card-body">
                                        <div class="d-flex justify-content-between align-items-center">
                                            <div>
                                                <h5 class="card-title">Targets Detected</h5>
                                                <span class="fs-3" id="targetCount">{{ status.targets_detected }}</span>
                                            </div>
                                            <i class="fa-solid fa-bullseye fa-2x text-danger"></i>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-6">
                        <div class="card mb-4">
                            <div class="card-header">
                                <i class="fa-solid fa-gauge-high"></i> System Metrics
                            </div>
                            <div class="card-body">
                                <div class="mb-3">
                                    <label class="form-label">Range Resolution: {{ "%.2f"|format(config.range_resolution) }} cm</label>
                                    <div class="progress">
                                        <div class="progress-bar bg-success" role="progressbar" 
                                            style="width: {{ (config.range_resolution * 100 / 0.2) * 100 }}%" 
                                            aria-valuenow="{{ config.range_resolution * 100 }}" 
                                            aria-valuemin="0" 
                                            aria-valuemax="20"></div>
                                    </div>
                                </div>
                                
                                <div class="mb-3">
                                    <label class="form-label">Velocity Error: {{ "%.2f"|format(config.velocity_error) }} m/s</label>
                                    <div class="progress">
                                        <div class="progress-bar bg-info" role="progressbar" 
                                            style="width: {{ (1 - config.velocity_error / 1.0) * 100 }}%" 
                                            aria-valuenow="{{ config.velocity_error }}" 
                                            aria-valuemin="0" 
                                            aria-valuemax="1.0"></div>
                                    </div>
                                </div>
                                
                                <div class="mb-3">
                                    <label class="form-label">Angular Resolution: {{ "%.1f"|format(config.angular_resolution) }}°</label>
                                    <div class="progress">
                                        <div class="progress-bar bg-warning" role="progressbar" 
                                            style="width: {{ (5 - config.angular_resolution) / 4 * 100 }}%" 
                                            aria-valuenow="{{ config.angular_resolution }}" 
                                            aria-valuemin="1" 
                                            aria-valuemax="5"></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-6">
                        <div class="card mb-4">
                            <div class="card-header">
                                <i class="fa-solid fa-bell"></i> Recent Alerts
                            </div>
                            <div class="card-body" style="max-height: 250px; overflow-y: auto;" id="recentAlerts">
                                {% if status.alerts %}
                                    {% for alert in status.alerts[-3:]|reverse %}
                                    <div class="alert {% if alert.acknowledged %}alert-secondary{% else %}alert-warning{% endif %} d-flex justify-content-between align-items-center">
                                        <div>
                                            <strong>{{ alert.type }}</strong>
                                            <div class="text-muted small">{{ alert.timestamp }}</div>
                                        </div>
                                        {% if not alert.acknowledged %}
                                        <a href="#" class="btn btn-sm btn-outline-dark acknowledge-btn" data-id="{{ alert.id }}">
                                            Acknowledge
                                        </a>
                                        {% else %}
                                        <span class="badge bg-success">Acknowledged</span>
                                        {% endif %}
                                    </div>
                                    {% endfor %}
                                {% else %}
                                    <div class="text-center text-muted py-4">
                                        <i class="fa-solid fa-circle-check fa-2x mb-2"></i>
                                        <p>No active alerts</p>
                                    </div>
                                {% endif %}
                            </div>
                            <div class="card-footer text-center">
                                <a href="/alerts" class="btn btn-sm btn-outline-primary">View All Alerts</a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Sidebar -->
            <div class="col-lg-3">
                <div class="card mb-4">
                    <div class="card-header bg-info text-white">
                        <i class="fa-solid fa-microchip"></i> Processing Performance
                    </div>
                    <div class="card-body">
                        <div class="mb-4">
                            <h6>Original Algorithm</h6>
                            <div class="d-flex justify-content-between">
                                <span>Processing Time:</span>
                                <strong id="originalTime">{{ "%.2f"|format(performance.original_processing_time * 1000) }} ms</strong>
                            </div>
                            <div class="progress mt-1 performance-bar">
                                <div class="progress-bar bg-secondary" role="progressbar" 
                                    style="width: {{ performance.original_processing_time * 100 }}%" 
                                    aria-valuenow="{{ performance.original_processing_time }}" 
                                    aria-valuemin="0" 
                                    aria-valuemax="1"></div>
                            </div>
                        </div>
                        
                        <div class="mb-4">
                            <h6>Optimized Algorithm</h6>
                            <div class="d-flex justify-content-between">
                                <span>Processing Time:</span>
                                <strong id="optimizedTime">{{ "%.2f"|format(performance.optimized_processing_time * 1000) }} ms</strong>
                            </div>
                            <div class="progress mt-1 performance-bar">
                                <div class="progress-bar bg-success" role="progressbar" 
                                    style="width: {{ performance.optimized_processing_time * 100 }}%" 
                                    aria-valuenow="{{ performance.optimized_processing_time }}" 
                                    aria-valuemin="0" 
                                    aria-valuemax="1"></div>
                            </div>
                        </div>
                        
                        <div class="d-flex justify-content-around text-center mt-4">
                            <div>
                                <div class="text-success">
                                    <i class="fa-solid fa-arrow-up fa-2x"></i>
                                </div>
                                <div class="small">Accuracy</div>
                                <strong id="accuracyImp">{{ "%.1f"|format(performance.accuracy_improvement) }}%</strong>
                            </div>
                            <div>
                                <div class="text-danger">
                                    <i class="fa-solid fa-arrow-down fa-2x"></i>
                                </div>
                                <div class="small">False Positives</div>
                                <strong id="fpReduction">{{ "%.1f"|format(performance.false_positive_reduction) }}%</strong>
                            </div>
                        </div>
                    </div>
                    <div class="card-footer text-center">
                        <a href="/performance" class="btn btn-sm btn-outline-info">Detailed Analysis</a>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header bg-success text-white">
                        <i class="fa-solid fa-info-circle"></i> System Information
                    </div>
                    <div class="card-body">
                        <ul class="list-group list-group-flush">
                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                Last Update
                                <span class="text-muted" id="lastUpdate">{{ status.last_update }}</span>
                            </li>
                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                Detection Sensitivity
                                <span class="badge bg-primary">{{ config.sensitivity|capitalize }}</span>
                            </li>
                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                Alert Email
                                <span class="text-muted small">{{ config.alert_email }}</span>
                            </li>
                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                Alert SMS
                                <span class="text-muted small">{{ config.alert_sms }}</span>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        // Initialize radar visualization
        const canvas = document.getElementById('detectionCanvas');
        const ctx = canvas.getContext('2d');
        canvas.width = canvas.parentElement.clientWidth;
        canvas.height = canvas.parentElement.clientHeight;
        
        // Store targets for animation
        let radarTargets = [];
        
        function drawRadar() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // Draw radar background
            const centerX = canvas.width / 2;
            const centerY = canvas.height / 2;
            const radius = Math.min(centerX, centerY) - 20;
            
            // Radar circles
            ctx.strokeStyle = 'rgba(0, 150, 0, 0.2)';
            ctx.lineWidth = 1;
            for (let i = 1; i <= 5; i++) {
                ctx.beginPath();
                ctx.arc(centerX, centerY, radius * i / 5, 0, Math.PI * 2);
                ctx.stroke();
            }
            
            // Radar lines
            for (let i = 0; i < 8; i++) {
                const angle = (Math.PI * 2 * i) / 8;
                ctx.beginPath();
                ctx.moveTo(centerX, centerY);
                ctx.lineTo(
                    centerX + Math.cos(angle) * radius,
                    centerY + Math.sin(angle) * radius
                );
                ctx.stroke();
            }
            
            // Draw rotating line
            const now = new Date();
            const sweepAngle = (now.getMilliseconds() / 1000) * Math.PI * 2;
            
            ctx.strokeStyle = 'rgba(0, 255, 0, 0.7)';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.lineTo(
                centerX + Math.cos(sweepAngle) * radius,
                centerY + Math.sin(sweepAngle) * radius
            );
            ctx.stroke();
            
            // Draw targets
            for (let i = 0; i < radarTargets.length; i++) {
                const target = radarTargets[i];
                const angle = target.angle;
                const distance = target.distance * radius / 30;  // Scale distance
                
                const x = centerX + Math.cos(angle) * distance;
                const y = centerY + Math.sin(angle) * distance;
                
                // Set color based on target type
                if (target.type === 'human') ctx.fillStyle = 'rgba(13, 110, 253, 0.8)';
                else if (target.type === 'vehicle') ctx.fillStyle = 'rgba(220, 53, 69, 0.8)';
                else if (target.type === 'animal') ctx.fillStyle = 'rgba(25, 135, 84, 0.8)';
                else ctx.fillStyle = 'rgba(108, 117, 125, 0.8)';
                
                ctx.beginPath();
                ctx.arc(x, y, 8, 0, Math.PI * 2);
                ctx.fill();
                
                // Draw velocity vector
                const velocityAngle = angle + (Math.random() - 0.5) * Math.PI/2;
                const velocityLength = target.speed * 5;
                
                ctx.strokeStyle = 'rgba(255, 193, 7, 0.7)';
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.moveTo(x, y);
                ctx.lineTo(
                    x + Math.cos(velocityAngle) * velocityLength,
                    y + Math.sin(velocityAngle) * velocityLength
                );
                ctx.stroke();
                
                // Draw arrowhead
                ctx.fillStyle = 'rgba(255, 193, 7, 0.7)';
                ctx.beginPath();
                ctx.moveTo(
                    x + Math.cos(velocityAngle) * velocityLength,
                    y + Math.sin(velocityAngle) * velocityLength
                );
                ctx.lineTo(
                    x + Math.cos(velocityAngle - Math.PI/6) * (velocityLength - 8),
                    y + Math.sin(velocityAngle - Math.PI/6) * (velocityLength - 8)
                );
                ctx.lineTo(
                    x + Math.cos(velocityAngle + Math.PI/6) * (velocityLength - 8),
                    y + Math.sin(velocityAngle + Math.PI/6) * (velocityLength - 8)
                );
                ctx.closePath();
                ctx.fill();
                
                // Draw target ID
                ctx.fillStyle = '#000';
                ctx.font = '10px Arial';
                ctx.fillText(`T${target.id}`, x + 10, y - 10);
            }
            
            requestAnimationFrame(drawRadar);
        }
        
        drawRadar();
        
        // Update system status periodically
        function updateDashboard() {
            $.get('/system_status', function(data) {
                // Update status elements
                $('.system-health').text(data.system_health.charAt(0).toUpperCase() + data.system_health.slice(1));
                $('.system-health').removeClass('health-good health-warning health-critical')
                    .addClass('health-' + data.system_health);
                
                $('#targetCount').text(data.targets_detected);
                $('#operationStatus').text(data.operation.charAt(0).toUpperCase() + data.operation.slice(1));
                $('#lastUpdate').text(data.last_update);
                $('#alertCountBadge').text(data.alerts.filter(a => !a.acknowledged).length);
            });
            
            // Update performance metrics
            $.get('/performance_data', function(data) {
                $('#originalTime').text((data.original_processing_time * 1000).toFixed(0) + ' ms');
                $('#optimizedTime').text((data.optimized_processing_time * 1000).toFixed(0) + 'ms');
                $('#accuracyImp').text(data.accuracy_improvement.toFixed(1) + '%');
                $('#fpReduction').text(data.false_positive_reduction.toFixed(1) + '%');
                
                // Update progress bars
                $('.progress-bar.bg-secondary').css('width', (data.original_processing_time * 100) + '%');
                $('.progress-bar.bg-success').css('width', (data.optimized_processing_time * 100) + '%');
            });
            
            // Update recent alerts
            $.get('/alert_counts', function(alertData) {
                if (alertData.total_active > 0) {
                    $.get('/alerts?partial=1', function(html) {
                        $('#recentAlerts').html(html);
                    });
                }
            });
            
            // Update targets on radar
            $.get('/targets?json=1', function(targets) {
                radarTargets = [];
        
                targets.forEach(target => {
                    if (target.history.length > 0) {
                        // Use the last position from history
                        const lastPos = target.history[target.history.length - 1];

                        const displayType = target.type === 'unknown' ? 'other' : target.type;
            
                        // Convert to radar coordinates
                        radarTargets.push({
                            id: target.id,
                            type: displayType,
                            angle: Math.atan2(lastPos.y, lastPos.x),
                            distance: Math.sqrt(lastPos.x*lastPos.x + lastPos.y*lastPos.y),
                            speed: target.max_speed || 1.0
                        });
                    }
                });
            });
        }
        
        // Acknowledge alert
        $(document).on('click', '.acknowledge-btn', function(e) {
            e.preventDefault();
            const alertId = $(this).data('id');
            
            $.post('/acknowledge_alert/' + alertId, function() {
                updateDashboard();
            });
        });
        
        // Update dashboard every 2 seconds
        setInterval(updateDashboard, 2000);
        updateDashboard();  // Initial update
    </script>
</body>
</html>
""")

# Configuration
with open('templates/config.html', 'w', encoding='utf-8') as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>mmWave Radar - Configuration</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        .config-card { transition: all 0.3s; }
        .config-card:hover { transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,0,0,0.1); }
        .section-title { border-bottom: 2px solid #0d6efd; padding-bottom: 10px; margin-bottom: 20px; }
        .form-switch .form-check-input { width: 3em; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="/">
                <i class="fa-solid fa-radar"></i> mmWave Radar System
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="/">
                            <i class="fa-solid fa-gauge"></i> Dashboard
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link active" href="/config">
                            <i class="fa-solid fa-sliders"></i> Configuration
                        </a>
                    </li>
                    <li class="nav-item position-relative">
                        <a class="nav-link" href="/alerts">
                            <i class="fa-solid fa-bell"></i> Alerts
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/performance">
                            <i class="fa-solid fa-chart-line"></i> Performance
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/targets">
                            <i class="fa-solid fa-bullseye"></i> Targets
                        </a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="row">
            <div class="col-lg-8 mx-auto">
                <div class="card config-card border-primary">
                    <div class="card-header bg-primary text-white">
                        <i class="fa-solid fa-sliders"></i> System Configuration
                    </div>
                    <div class="card-body">
                        <form id="configForm">
                            <h4 class="section-title">
                                <i class="fa-solid fa-microscope"></i> Detection Parameters
                            </h4>
                            
                            <div class="row mb-4">
                                <div class="col-md-6 mb-3">
                                    <label class="form-label">Range Resolution (cm)</label>
                                    <input type="number" class="form-control" name="range_res" 
                                        min="0.1" max="20" step="0.1"
                                        value="{{ "%.1f"|format(config.range_resolution) }}">
                                    <div class="form-text">
                                        Lower values provide finer range resolution
                                    </div>
                                </div>
                                
                                <div class="col-md-6 mb-3">
                                    <label class="form-label">Velocity Estimation Error (m/s)</label>
                                    <input type="number" class="form-control" name="vel_error" 
                                        min="0.01" max="1.0" step="0.01"
                                        value="{{ "%.2f"|format(config.velocity_error) }}">
                                    <div class="form-text">
                                        Lower values provide more accurate velocity measurements
                                    </div>
                                </div>
                                
                                <div class="col-md-6 mb-3">
                                    <label class="form-label">Angular Resolution (°)</label>
                                    <input type="number" class="form-control" name="ang_res" 
                                        min="0.1" max="5.0" step="0.1"
                                        value="{{ "%.1f"|format(config.angular_resolution) }}">
                                    <div class="form-text">
                                        Lower values provide finer angular resolution
                                    </div>
                                </div>
                                
                                <div class="col-md-6 mb-3">
                                    <label class="form-label">Detection Threshold</label>
                                    <input type="number" class="form-control" name="threshold" 
                                        min="1.0" max="10.0" step="0.1"
                                        value="{{ "%.1f"|format(config.detection_threshold) }}">
                                    <div class="form-text">
                                        Higher values reduce false positives but may miss weak targets
                                    </div>
                                </div>
                                
                                <div class="col-md-12 mb-3">
                                    <label class="form-label">Detection Sensitivity</label>
                                    <select class="form-select" name="sensitivity">
                                        <option value="low" {% if config.sensitivity == 'low' %}selected{% endif %}>Low</option>
                                        <option value="medium" {% if config.sensitivity == 'medium' %}selected{% endif %}>Medium</option>
                                        <option value="high" {% if config.sensitivity == 'high' %}selected{% endif %}>High</option>
                                    </select>
                                    <div class="form-text">
                                        Higher sensitivity detects smaller movements but may increase false alarms
                                    </div>
                                </div>
                            </div>
                            
                            <h4 class="section-title">
                                <i class="fa-solid fa-bell"></i> Alert Settings
                            </h4>
                            
                            <div class="row mb-4">
                                <div class="col-md-6 mb-3">
                                    <label class="form-label">Email for Alerts</label>
                                    <input type="email" class="form-control" name="alert_email" 
                                        value="{{ config.alert_email }}">
                                </div>
                                
                                <div class="col-md-6 mb-3">
                                    <label class="form-label">SMS for Alerts</label>
                                    <input type="tel" class="form-control" name="alert_sms" 
                                        value="{{ config.alert_sms }}">
                                </div>
                                
                                <div class="col-md-12 mb-3">
                                    <div class="form-check form-switch">
                                        <input class="form-check-input" type="checkbox" id="emailAlerts" checked>
                                        <label class="form-check-label" for="emailAlerts">
                                            Enable Email Alerts
                                        </label>
                                    </div>
                                    
                                    <div class="form-check form-switch">
                                        <input class="form-check-input" type="checkbox" id="smsAlerts" checked>
                                        <label class="form-check-label" for="smsAlerts">
                                            Enable SMS Alerts
                                        </label>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="d-grid gap-2 d-md-flex justify-content-md-end mt-4">
                                <button type="button" class="btn btn-secondary" id="resetBtn">
                                    <i class="fa-solid fa-rotate-left"></i> Reset to Defaults
                                </button>
                                <button type="submit" class="btn btn-primary">
                                    <i class="fa-solid fa-floppy-disk"></i> Save Configuration
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
                
                <div class="card config-card border-warning mt-4">
                    <div class="card-header bg-warning text-dark">
                        <i class="fa-solid fa-triangle-exclamation"></i> System Maintenance
                    </div>
                    <div class="card-body">
                        <div class="d-grid gap-2">
                            <button class="btn btn-outline-warning mb-2" id="rebootBtn">
                                <i class="fa-solid fa-rotate"></i> Reboot System
                            </button>
                            <button class="btn btn-outline-danger" id="shutdownBtn">
                                <i class="fa-solid fa-power-off"></i> Shutdown System
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        $('#configForm').submit(function(e) {
            e.preventDefault();
            
            $.ajax({
                type: 'POST',
                url: '/config',
                data: $(this).serialize(),
                success: function() {
                    alert('Configuration saved successfully!');
                },
                error: function() {
                    alert('Error saving configuration. Please try again.');
                }
            });
        });
        
        $('#resetBtn').click(function() {
            if (confirm('Are you sure you want to reset all settings to default values?')) {
                // Reset form values to original defaults
                $('input[name="range_res"]').val('5.0');
                $('input[name="vel_error"]').val('0.1');
                $('input[name="ang_res"]').val('1.5');
                $('input[name="threshold"]').val('2.5');
                $('select[name="sensitivity"]').val('medium');
                $('input[name="alert_email"]').val('admin@example.com');
                $('input[name="alert_sms"]').val('+1234567890');
                
                alert('Configuration reset to defaults. Click Save to apply.');
            }
        });
        
        // Add functionality to reboot and shutdown buttons
        $(document).on('click', '#rebootBtn', function() {
            if (confirm('Are you sure you want to reboot the system? This will reset all data.')) {
                $.post('/reboot_system', function() {
                    alert('System is rebooting. Page will refresh shortly...');
                    setTimeout(() => location.reload(), 3000);
                });
            }
        });
    
        $(document).on('click', '#shutdownBtn', function() {
            if (confirm('WARNING: This will shut down the entire radar system. Are you absolutely sure?')) {
                $.post('/shutdown_system', function() {
                    alert('System is shutting down. You will be redirected...');
                    setTimeout(() => window.location.href = '/', 2000);
                });
            }
        });
    </script>
</body>
</html>
""")

# Alerts
with open('templates/alerts.html', 'w', encoding='utf-8') as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>mmWave Radar - Alert Management</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css">
    <style>
        .alert-critical { background-color: #ffdddd; border-left: 4px solid #dc3545; }
        .alert-warning { background-color: #fff3cd; border-left: 4px solid #ffc107; }
        .alert-info { background-color: #d1ecf1; border-left: 4px solid #0dcaf0; }
        .alert-acknowledged { opacity: 0.7; }
        .alert-card { transition: all 0.3s; }
        .alert-card:hover { transform: translateY(-3px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="/">
                <i class="fa-solid fa-radar"></i> mmWave Radar System
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="/">
                            <i class="fa-solid fa-gauge"></i> Dashboard
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/config">
                            <i class="fa-solid fa-sliders"></i> Configuration
                        </a>
                    </li>
                    <li class="nav-item position-relative">
                        <a class="nav-link active" href="/alerts">
                            <i class="fa-solid fa-bell"></i> Alerts
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/performance">
                            <i class="fa-solid fa-chart-line"></i> Performance
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/targets">
                            <i class="fa-solid fa-bullseye"></i> Targets
                        </a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h1>
                <i class="fa-solid fa-bell"></i> Alert Management
            </h1>
            <div>
                <button class="btn btn-outline-danger" id="clearAlertsBtn">
                    <i class="fa-solid fa-trash-can"></i> Clear All
                </button>
            </div>
        </div>
        
        <div class="row" id="alertSummary">
            <div class="col-md-3 mb-4">
                <div class="card alert-card border-danger">
                    <div class="card-body text-center">
                        <div class="text-danger mb-2">
                            <i class="fa-solid fa-circle-exclamation fa-3x"></i>
                        </div>
                        <h3 class="text-danger" id="activeAlertCount">0</h3>
                        <p class="text-muted">Active Alerts</p>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3 mb-4">
                <div class="card alert-card border-warning">
                    <div class="card-body text-center">
                        <div class="text-warning mb-2">
                            <i class="fa-solid fa-triangle-exclamation fa-3x"></i>
                        </div>
                        <h3 class="text-warning" id="motionAlertCount">0</h3>
                        <p class="text-muted">Motion Alerts</p>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3 mb-4">
                <div class="card alert-card border-info">
                    <div class="card-body text-center">
                        <div class="text-info mb-2">
                            <i class="fa-solid fa-gear fa-3x"></i>
                        </div>
                        <h3 class="text-info" id="systemAlertCount">0</h3>
                        <p class="text-muted">System Alerts</p>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3 mb-4">
                <div class="card alert-card border-success">
                    <div class="card-body text-center">
                        <div class="text-success mb-2">
                            <i class="fa-solid fa-circle-check fa-3x"></i>
                        </div>
                        <h3 class="text-success" id="acknowledgedAlertCount">0</h3>
                        <p class="text-muted">Acknowledged</p>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="card mb-4">
            <div class="card-header">
                <ul class="nav nav-tabs card-header-tabs">
                    <li class="nav-item">
                        <a class="nav-link active" href="#active-alerts">Active Alerts</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#acknowledged-alerts">Acknowledged</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#all-alerts">All Alerts</a>
                    </li>
                </ul>
            </div>
            <div class="card-body">
                <div class="tab-content">
                    <div class="tab-pane fade show active" id="active-alerts">
                        <div class="table-responsive">
                            <table class="table table-hover" id="activeAlertsTable">
                                <thead class="table-light">
                                    <tr>
                                        <th>ID</th>
                                        <th>Type</th>
                                        <th>Timestamp</th>
                                        <th>Target</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for alert in alerts if not alert.acknowledged %}
                                    <tr class="{% if alert.type == 'System Critical' %}table-danger{% elif alert.type == 'Motion Detected' %}table-warning{% else %}table-info{% endif %}">
                                        <td>{{ alert.id }}</td>
                                        <td>{{ alert.type }}</td>
                                        <td>{{ alert.timestamp }}</td>
                                        <td>
                                            {% if alert.target %}
                                            Target #{{ alert.target.id }} ({{ "%.1f"|format(alert.target.avg_range) }}m)
                                            {% else %}
                                            System
                                            {% endif %}
                                        </td>
                                        <td>
                                            <button class="btn btn-sm btn-outline-primary acknowledge-btn" data-id="{{ alert.id }}">
                                                <i class="fa-solid fa-check"></i> Acknowledge
                                            </button>
                                        </td>
                                    </tr>
                                    {% else %}
                                    <tr>
                                        <td colspan="5" class="text-center py-4">
                                            <i class="fa-solid fa-face-smile-beam fa-3x text-success mb-3"></i>
                                            <h4>No Active Alerts</h4>
                                            <p class="text-muted">All alerts have been acknowledged</p>
                                        </td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    
                    <div class="tab-pane fade" id="acknowledged-alerts">
                        <div class="table-responsive">
                            <table class="table table-hover">
                                <thead class="table-light">
                                    <tr>
                                        <th>ID</th>
                                        <th>Type</th>
                                        <th>Timestamp</th>
                                        <th>Target</th>
                                        <th>Acknowledged</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for alert in alerts if alert.acknowledged %}
                                    <tr class="table-secondary">
                                        <td>{{ alert.id }}</td>
                                        <td>{{ alert.type }}</td>
                                        <td>{{ alert.timestamp }}</td>
                                        <td>
                                            {% if alert.target %}
                                            Target #{{ alert.target.id }} ({{ "%.1f"|format(alert.target.avg_range) }}m)
                                            {% else %}
                                            System
                                            {% endif %}
                                        </td>
                                        <td>
                                            <span class="badge bg-success">Yes</span>
                                        </td>
                                    </tr>
                                    {% else %}
                                    <tr>
                                        <td colspan="5" class="text-center py-4">
                                            <i class="fa-solid fa-inbox fa-3x text-muted mb-3"></i>
                                            <h4>No Acknowledged Alerts</h4>
                                            <p class="text-muted">No alerts have been acknowledged yet</p>
                                        </td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    
                    <div class="tab-pane fade" id="all-alerts">
                        <div class="table-responsive">
                            <table class="table table-hover">
                                <thead class="table-light">
                                    <tr>
                                        <th>ID</th>
                                        <th>Type</th>
                                        <th>Timestamp</th>
                                        <th>Target</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for alert in alerts %}
                                    <tr class="{% if alert.acknowledged %}table-secondary{% elif alert.type == 'System Critical' %}table-danger{% elif alert.type == 'Motion Detected' %}table-warning{% else %}table-info{% endif %}">
                                        <td>{{ alert.id }}</td>
                                        <td>{{ alert.type }}</td>
                                        <td>{{ alert.timestamp }}</td>
                                        <td>
                                            {% if alert.target %}
                                            Target #{{ alert.target.id }} ({{ "%.1f"|format(alert.target.avg_range) }}m)
                                            {% else %}
                                            System
                                            {% endif %}
                                        </td>
                                        <td>
                                            {% if alert.acknowledged %}
                                            <span class="badge bg-success">Acknowledged</span>
                                            {% else %}
                                            <span class="badge bg-warning">Active</span>
                                            {% endif %}
                                        </td>
                                    </tr>
                                    {% else %}
                                    <tr>
                                        <td colspan="5" class="text-center py-4">
                                            <i class="fa-solid fa-inbox fa-3x text-muted mb-3"></i>
                                            <h4>No Alerts</h4>
                                            <p class="text-muted">No alerts have been generated</p>
                                        </td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Update alert counts
        function updateAlertCounts() {
            $.get('/alert_counts', function(data) {
                $('#activeAlertCount').text(data.total_active);
                $('#motionAlertCount').text(data.motion_alerts);
                $('#systemAlertCount').text(data.system_alerts);
                $('#acknowledgedAlertCount').text(data.acknowledged);
            });
        }
        
        // Acknowledge alert
        $(document).on('click', '.acknowledge-btn', function() {
            const alertId = $(this).data('id');
            $.post('/acknowledge_alert/' + alertId, function() {
                // Refresh active alerts
                $.get('/alerts?partial=active', function(html) {
                    $('#activeAlertsTable tbody').html(html);
                    updateAlertCounts();
                });
            });
        });
        
        // Clear all alerts
        $('#clearAlertsBtn').click(function() {
            if (confirm('Are you sure you want to clear all alerts? This cannot be undone.')) {
                // Find all active alert IDs
                const alertIds = [];
                $('.acknowledge-btn').each(function() {
                    alertIds.push($(this).data('id'));
                });
                
                // Acknowledge all alerts
                alertIds.forEach(id => {
                    $.post('/acknowledge_alert/' + id);
                });
                
                // Refresh after a short delay
                setTimeout(function() {
                    location.reload();
                }, 500);
            }
        });
        
        // Initialize and update every 5 seconds
        updateAlertCounts();
        setInterval(updateAlertCounts, 5000);
    </script>
</body>
</html>
""")

# Performance
with open('templates/performance.html', 'w', encoding='utf-8') as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>mmWave Radar - Performance</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        .perf-card { transition: transform 0.3s; }
        .perf-card:hover { transform: translateY(-5px); }
        .metric-value { font-size: 2rem; font-weight: 600; }
        .metric-label { font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; }
        .improvement { color: #28a745; }
        .decline { color: #dc3545; }
        .comparison-bar { height: 30px; border-radius: 15px; }
        .algorithm-card { border-left: 4px solid; }
        .original-algo { border-left-color: #6c757d; }
        .optimized-algo { border-left-color: #28a745; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="/">
                <i class="fa-solid fa-radar"></i> mmWave Radar System
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="/">
                            <i class="fa-solid fa-gauge"></i> Dashboard
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/config">
                            <i class="fa-solid fa-sliders"></i> Configuration
                        </a>
                    </li>
                    <li class="nav-item position-relative">
                        <a class="nav-link" href="/alerts">
                            <i class="fa-solid fa-bell"></i> Alerts
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link active" href="/performance">
                            <i class="fa-solid fa-chart-line"></i> Performance
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/targets">
                            <i class="fa-solid fa-bullseye"></i> Targets
                        </a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <h1 class="mb-4">
            <i class="fa-solid fa-chart-line"></i> Algorithm Performance
        </h1>
        
        <div class="row mb-4" id="performanceMetrics">
            <div class="col-md-3">
                <div class="card perf-card mb-4">
                    <div class="card-body text-center">
                        <div class="metric-value improvement" id="accuracyImp">
                            {{ "%.1f"|format(performance.accuracy_improvement) }}%
                        </div>
                        <div class="metric-label text-muted">Accuracy Improvement</div>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3">
                <div class="card perf-card mb-4">
                    <div class="card-body text-center">
                        <div class="metric-value decline" id="fpReduction">
                            {{ "%.1f"|format(performance.false_positive_reduction) }}%
                        </div>
                        <div class="metric-label text-muted">False Positive Reduction</div>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3">
                <div class="card perf-card mb-4">
                    <div class="card-body text-center">
                        <div class="metric-value" id="originalTime">
                            {{ "%.0f"|format(performance.original_processing_time * 1000) }}ms
                        </div>
                        <div class="metric-label text-muted">Original Processing</div>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3">
                <div class="card perf-card mb-4">
                    <div class="card-body text-center">
                        <div class="metric-value improvement" id="optimizedTime">
                            {{ "%.0f"|format(performance.optimized_processing_time * 1000) }}ms
                        </div>
                        <div class="metric-label text-muted">Optimized Processing</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-md-6 mb-4">
                <div class="card">
                    <div class="card-header">
                        Processing Time Comparison
                    </div>
                    <div class="card-body">
                        <div class="position-relative" style="height: 300px;">
                            <canvas id="processingTimeChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="col-md-6 mb-4">
                <div class="card">
                    <div class="card-header">
                        Detection Accuracy
                    </div>
                    <div class="card-body">
                        <div class="position-relative" style="height: 300px;">
                            <canvas id="accuracyChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-md-12">
                <div class="card mb-4">
                    <div class="card-header">
                        Algorithm Comparison
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <div class="card algorithm-card original-algo mb-4">
                                    <div class="card-header bg-light">
                                        <i class="fa-solid fa-microchip"></i> Original Algorithm
                                    </div>
                                    <div class="card-body">
                                        <ul class="list-group list-group-flush">
                                            <li class="list-group-item">
                                                <i class="fa-solid fa-clock"></i> Processing Time: 
                                                <strong>{{ "%.0f"|format(performance.original_processing_time * 1000) }}ms</strong>
                                            </li>
                                            <li class="list-group-item">
                                                <i class="fa-solid fa-bullseye"></i> Detection Accuracy: 
                                                <strong>{{ "%.1f"|format(85 - performance.accuracy_improvement) }}%</strong>
                                            </li>
                                            <li class="list-group-item">
                                                <i class="fa-solid fa-triangle-exclamation"></i> False Positives: 
                                                <strong>{{ "%.1f"|format(12 - performance.false_positive_reduction) }}%</strong>
                                            </li>
                                            <li class="list-group-item">
                                                <i class="fa-solid fa-memory"></i> Memory Usage: 
                                                <strong>High</strong>
                                            </li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="col-md-6">
                                <div class="card algorithm-card optimized-algo mb-4">
                                    <div class="card-header bg-light">
                                        <i class="fa-solid fa-rocket"></i> Optimized Algorithm
                                    </div>
                                    <div class="card-body">
                                        <ul class="list-group list-group-flush">
                                            <li class="list-group-item">
                                                <i class="fa-solid fa-clock"></i> Processing Time: 
                                                <strong class="improvement">{{ "%.0f"|format(performance.optimized_processing_time * 1000) }}ms</strong>
                                            </li>
                                            <li class="list-group-item">
                                                <i class="fa-solid fa-bullseye"></i> Detection Accuracy: 
                                                <strong class="improvement">{{ "%.1f"|format(85) }}%</strong>
                                            </li>
                                            <li class="list-group-item">
                                                <i class="fa-solid fa-triangle-exclamation"></i> False Positives: 
                                                <strong class="improvement">{{ "%.1f"|format(12 - performance.false_positive_reduction) }}%</strong>
                                            </li>
                                            <li class="list-group-item">
                                                <i class="fa-solid fa-memory"></i> Memory Usage: 
                                                <strong class="improvement">Moderate</strong>
                                            </li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="d-grid gap-2">
                            <a class="btn btn-outline-primary" href="/export_performance_report">
                                <i class="fa-solid fa-download"></i> Export Performance Report
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        // Initialize charts
        const procCtx = document.getElementById('processingTimeChart').getContext('2d');
        const procChart = new Chart(procCtx, {
            type: 'bar',
            data: {
                labels: ['FFT', 'Clutter Suppression', 'Doppler Processing', 'Target Classification'],
                datasets: [{
                    label: 'Original Algorithm',
                    data: [25, 18, 32, 45],
                    backgroundColor: 'rgba(108, 117, 125, 0.7)'
                }, {
                    label: 'Optimized Algorithm',
                    data: [20, 12, 25, 30],
                    backgroundColor: 'rgba(40, 167, 69, 0.7)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Processing Time (ms)'
                        }
                    }
                }
            }
        });
        
        const accCtx = document.getElementById('accuracyChart').getContext('2d');
        const accChart = new Chart(accCtx, {
            type: 'radar',
            data: {
                labels: ['Range Accuracy', 'Velocity Accuracy', 'Angle Accuracy', 'Detection Rate', 'False Positives'],
                datasets: [{
                    label: 'Original Algorithm',
                    data: [75, 82, 78, 80, 65],
                    fill: true,
                    backgroundColor: 'rgba(108, 117, 125, 0.2)',
                    borderColor: 'rgb(108, 117, 125)',
                    pointBackgroundColor: 'rgb(108, 117, 125)',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: 'rgb(108, 117, 125)'
                }, {
                    label: 'Optimized Algorithm',
                    data: [85, 90, 88, 92, 85],
                    fill: true,
                    backgroundColor: 'rgba(40, 167, 69, 0.2)',
                    borderColor: 'rgb(40, 167, 69)',
                    pointBackgroundColor: 'rgb(40, 167, 69)',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: 'rgb(40, 167, 69)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        angleLines: {
                            display: true
                        },
                        suggestedMin: 50,
                        suggestedMax: 100
                    }
                }
            }
        });
        
        // Update performance metrics
        function updatePerformance() {
            $.get('/performance_data', function(data) {
                $('#accuracyImp').text(data.accuracy_improvement.toFixed(1) + '%');
                $('#fpReduction').text(data.false_positive_reduction.toFixed(1) + '%');
                $('#originalTime').text((data.original_processing_time * 1000).toFixed(0) + ' ms');
                $('#optimizedTime').text((data.optimized_processing_time * 1000).toFixed(0) + 'ms');
            });
        }
        
        // Update every 5 seconds
        setInterval(updatePerformance, 5000);
        updatePerformance();
    </script>
</body>
</html>
""")

# Targets
with open('templates/targets.html', 'w', encoding='utf-8') as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>mmWave Radar - Target Tracking</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css">
    <style>
        .target-card { transition: transform 0.3s; }
        .target-card:hover { transform: translateY(-5px); }
        .target-type-human { border-left: 4px solid #0d6efd; }
        .target-type-vehicle { border-left: 4px solid #dc3545; }
        .target-type-animal { border-left: 4px solid #198754; }
        .target-type-other { border-left: 4px solid #6c757d; }
        .trajectory-map { height: 400px; background: #f8f9fa; border-radius: 5px; }
        .badge-human { background-color: #0d6efd; }
        .badge-vehicle { background-color: #dc3545; }
        .badge-animal { background-color: #198754; }
        .badge-unknown { background-color: #ffc107; color: black; } /* Changed unknown to yellow */
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="/">
                <i class="fa-solid fa-radar"></i> mmWave Radar System
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="/">
                            <i class="fa-solid fa-gauge"></i> Dashboard
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/config">
                            <i class="fa-solid fa-sliders"></i> Configuration
                        </a>
                    </li>
                    <li class="nav-item position-relative">
                        <a class="nav-link" href="/alerts">
                            <i class="fa-solid fa-bell"></i> Alerts
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/performance">
                            <i class="fa-solid fa-chart-line"></i> Performance
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link active" href="/targets">
                            <i class="fa-solid fa-bullseye"></i> Targets
                        </a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <h1 class="mb-4">
            <i class="fa-solid fa-bullseye"></i> Target Tracking
        </h1>
        
        <div class="row mb-4" id="targetSummary">
            <div class="col-md-3">
                <div class="card target-card target-type-human mb-4">
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <div>
                                <h5 class="card-title">Human Targets</h5>
                                <h2 class="text-primary" id="humanTargets">0</h2>
                            </div>
                            <i class="fa-solid fa-person fa-3x text-primary"></i>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3">
                <div class="card target-card target-type-vehicle mb-4">
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <div>
                                <h5 class="card-title">Vehicle Targets</h5>
                                <h2 class="text-danger" id="vehicleTargets">0</h2>
                            </div>
                            <i class="fa-solid fa-car fa-3x text-danger"></i>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3">
                <div class="card target-card target-type-animal mb-4">
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <div>
                                <h5 class="card-title">Animal Targets</h5>
                                <h2 class="text-success" id="animalTargets">0</h2>
                            </div>
                            <i class="fa-solid fa-dog fa-3x text-success"></i>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3">
                <div class="card target-card target-type-other mb-4">
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <div>
                                <h5 class="card-title">Other Targets</h5>
                                <h2 class="text-secondary" id="otherTargets">0</h2>
                            </div>
                            <i class="fa-solid fa-question fa-3x text-secondary"></i>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="card mb-4">
            <div class="card-header">
                <i class="fa-solid fa-location-dot"></i> Target Trajectory Map
            </div>
            <div class="card-body">
                <div class="trajectory-map" id="trajectoryMap"></div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">
                <i class="fa-solid fa-table-list"></i> Target Tracking History
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-hover" id="targetTable">
                        <thead class="table-light">
                            <tr>
                                <th>ID</th>
                                <th>Type</th>
                                <th>First Detected</th>
                                <th>Last Detected</th>
                                <th>Duration</th>
                                <th>Max Speed</th>
                                <th>Avg Range</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for target in targets %}
                            <tr>
                                <td>{{ target.id }}</td>
                                <td>
                                    <span class="badge badge-{{ target.type }}">{{ target.type|capitalize }}</span>
                                </td>
                                <td>{{ target.first_detected }}</td>
                                <td>{{ target.last_detected }}</td>
                                <td>{{ target.duration }}</td>
                                <td>{{ target.max_speed }}</td>
                                <td>{{ target.avg_range }}</td>
                                <td>
                                    {% if target.status == 'active' %}
                                    <span class="badge bg-success">Active</span>
                                    {% else %}
                                    <span class="badge bg-secondary">Inactive</span>
                                    {% endif %}
                                </td>
                                <td>
                                    <button class="btn btn-sm btn-outline-primary view-trajectory" data-id="{{ target.id }}">
                                        <i class="fa-solid fa-map-location-dot"></i> Trajectory
                                    </button>
                                </td>
                            </tr>
                            {% else %}
                            <tr>
                                <td colspan="9" class="text-center py-4">
                                    <i class="fa-solid fa-bullseye fa-3x text-muted mb-3"></i>
                                    <h4>No Targets Detected</h4>
                                    <p class="text-muted">No targets have been detected yet</p>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <!-- Trajectory Modal -->
    <div class="modal fade" id="trajectoryModal" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Target Trajectory - <span id="targetIdHeader"></span></h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div id="targetTrajectoryMap" style="height: 400px; background: #f8f9fa;"></div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                </div>
            </div>
        </div>
    </div>

    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>
    <script>
        // Update target counts with actual data from tracking history
        // Function to update target counts
        function updateTargetCounts() {
            $.get('/target_data', function(data) {
                $('#humanTargets').text(data.human_targets);
                $('#vehicleTargets').text(data.vehicle_targets);
                $('#animalTargets').text(data.animal_targets);
                $('#otherTargets').text(data.other_targets);
                
                // Also update the target table if needed
                refreshTargetTable();
            });
        }             
        
        $(document).ready(function() {
            // Initialize DataTable
            $('#targetTable').DataTable({
                order: [[2, 'desc']],
                pageLength: 5
            });
            
            updateTargetCounts();  // Initial update

            // Update target counts every 2 seconds
            setInterval(updateTargetCounts, 2000);

            // Initialize trajectory map
            const mapEl = document.getElementById('trajectoryMap');
            const ctx = mapEl.getContext('2d');
            mapEl.width = mapEl.parentElement.clientWidth;
            mapEl.height = 400;
            
            // Store target histories for visualization
            const targetHistories = [
                {% for target in targets %}
                {
                    id: {{ target.id }},
                    type: "{{ target.type }}",
                    history: {{ target.history | tojson }},
                    status: "{{ target.status }}"
                }{% if not loop.last %},{% endif %}
                {% endfor %}
            ];
            
            // Draw trajectory map with actual data
            function drawTrajectory() {
                ctx.clearRect(0, 0, mapEl.width, mapEl.height);
                
                // Draw radar at bottom center
                const radarX = mapEl.width / 2;
                const radarY = mapEl.height - 20;
                
                // Draw radar circles
                ctx.strokeStyle = 'rgba(0, 150, 0, 0.2)';
                ctx.lineWidth = 1;
                const maxRange = 30; // meters
                const maxRadius = Math.min(mapEl.width, mapEl.height) * 0.4;
                
                for (let i = 1; i <= 5; i++) {
                    const radius = maxRadius * i / 5;
                    ctx.beginPath();
                    ctx.arc(radarX, radarY, radius, 0, Math.PI * 2);
                    ctx.stroke();
                }
                
                // Draw radar lines
                for (let i = 0; i < 8; i++) {
                    const angle = (Math.PI * 2 * i) / 8;
                    ctx.beginPath();
                    ctx.moveTo(radarX, radarY);
                    ctx.lineTo(
                        radarX + Math.cos(angle) * maxRadius,
                        radarY + Math.sin(angle) * maxRadius
                    );
                    ctx.stroke();
                }
                
                // Draw rotating line
                const now = new Date();
                const sweepAngle = (now.getMilliseconds() / 1000) * Math.PI * 2;
                
                ctx.strokeStyle = 'rgba(0, 255, 0, 0.7)';
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.moveTo(radarX, radarY);
                ctx.lineTo(
                    radarX + Math.cos(sweepAngle) * maxRadius,
                    radarY + Math.sin(sweepAngle) * maxRadius
                );
                ctx.stroke();
                
                // Draw each target's trajectory
                targetHistories.forEach(target => {
                    if (target.history.length === 0) return;
                    
                    // Set color based on target type
                    let color;
                    switch(target.type) {
                        case 'human': color = '#0d6efd'; break;
                        case 'vehicle': color = '#dc3545'; break;
                        case 'animal': color = '#198754'; break;
                        default: color = '#ffc107'; // yellow for unknown
                    }
                    
                    // Convert history points to canvas coordinates
                    const points = target.history.map(point => {
                        // Scale coordinates to fit canvas
                        const x = radarX + (point.x / 10) * (maxRadius * 0.8);
                        const y = radarY - (point.y / maxRange) * maxRadius;
                        return {x, y};
                    });
                    
                    // Draw the path
                    ctx.beginPath();
                    ctx.moveTo(points[0].x, points[0].y);
                    for (let i = 1; i < points.length; i++) {
                        ctx.lineTo(points[i].x, points[i].y);
                    }
                    ctx.strokeStyle = color + '80'; // semi-transparent
                    ctx.lineWidth = 2;
                    ctx.stroke();
                    
                    // Draw points
                    points.forEach((point, index) => {
                        ctx.beginPath();
                        ctx.arc(point.x, point.y, 4, 0, Math.PI * 2);
                        ctx.fillStyle = color;
                        ctx.fill();
                        
                        // Draw target ID at the first point
                        if (index === 0) {
                            ctx.fillStyle = '#000';
                            ctx.font = '10px Arial';
                            ctx.fillText(`T${target.id}`, point.x + 8, point.y - 8);
                        }
                    });
                });
            }
            
            drawTrajectory();
            
            // Handle window resize
            window.addEventListener('resize', function() {
                mapEl.width = mapEl.parentElement.clientWidth;
                drawTrajectory();
            }); 

            // Refresh target table data
            function refreshTargetTable() {
                $.get('/targets?partial=1', function(html) {
                    $('#targetTable tbody').html($(html).find('#targetTable tbody').html());
                    initializeTargetVisualization();
                });
            }

            // Initialize target visualization with current data
            function initializeTargetVisualization() {
                // Get updated target histories
                $.get('/targets?json=1', function(targets) {
                    targetHistories = targets;
                    drawTrajectory();
                });
            }
            
            // View trajectory
            $(document).on('click', '.view-trajectory', function() {
                const targetId = $(this).data('id');
                const target = targetHistories.find(t => t.id == targetId);
                
                if (!target || target.history.length < 2) {
                    alert('No trajectory data available for this target');
                    return;
                }
                
                $('#targetIdHeader').text('Target #' + target.id);
                const modal = new bootstrap.Modal(document.getElementById('trajectoryModal'));
                modal.show();
                
                // Initialize modal map
                const modalMap = document.getElementById('targetTrajectoryMap');
                const modalCtx = modalMap.getContext('2d');
                modalMap.width = modalMap.parentElement.clientWidth;
                modalMap.height = 400;
                
                // Draw modal map
                drawModalTrajectory(modalCtx, target);
            });
            
            function drawModalTrajectory(ctx, target) {
                ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
                
                // Draw radar at bottom center
                const radarX = ctx.canvas.width / 2;
                const radarY = ctx.canvas.height - 20;
                const maxRange = 30; // meters
                const maxRadius = Math.min(ctx.canvas.width, ctx.canvas.height) * 0.4;
                
                // Draw radar background
                ctx.strokeStyle = 'rgba(0, 150, 0, 0.2)';
                ctx.lineWidth = 1;
                for (let i = 1; i <= 5; i++) {
                    const radius = maxRadius * i / 5;
                    ctx.beginPath();
                    ctx.arc(radarX, radarY, radius, 0, Math.PI * 2);
                    ctx.stroke();
                }
                
                // Draw radar lines
                for (let i = 0; i < 8; i++) {
                    const angle = (Math.PI * 2 * i) / 8;
                    ctx.beginPath();
                    ctx.moveTo(radarX, radarY);
                    ctx.lineTo(
                        radarX + Math.cos(angle) * maxRadius,
                        radarY + Math.sin(angle) * maxRadius
                    );
                    ctx.stroke();
                }
                
                // Set color based on target type
                let color;
                switch(target.type) {
                    case 'human': color = '#0d6efd'; break;
                    case 'vehicle': color = '#dc3545'; break;
                    case 'animal': color = '#198754'; break;
                    default: color = '#ffc107'; // yellow for unknown
                }
                
                // Convert history points to canvas coordinates
                const points = target.history.map(point => {
                    const x = radarX + (point.x / 10) * (maxRadius * 0.8);
                    const y = radarY - (point.y / maxRange) * maxRadius;
                    return {x, y, timestamp: point.timestamp};
                });
                
                // Draw the path
                ctx.beginPath();
                ctx.moveTo(points[0].x, points[0].y);
                for (let i = 1; i < points.length; i++) {
                    ctx.lineTo(points[i].x, points[i].y);
                }
                ctx.strokeStyle = color;
                ctx.lineWidth = 3;
                ctx.stroke();
                
                // Draw points with timestamps
                points.forEach((point, index) => {
                    // Point color: green for start, red for end, target color for others
                    if (index === 0) {
                        ctx.fillStyle = '#28a745'; // start: green
                    } else if (index === points.length - 1) {
                        ctx.fillStyle = '#dc3545'; // end: red
                    } else {
                        ctx.fillStyle = color;
                    }
                    
                    ctx.beginPath();
                    ctx.arc(point.x, point.y, 6, 0, Math.PI * 2);
                    ctx.fill();
                    
                    // Draw timestamp for start and end points
                    if (index === 0 || index === points.length - 1) {
                        ctx.fillStyle = '#000';
                        ctx.font = '10px Arial';
                        ctx.fillText(point.timestamp, point.x + 8, point.y - 8);
                    }
                });
                
                // Draw radar position
                ctx.fillStyle = 'rgba(13, 110, 253, 0.8)';
                ctx.beginPath();
                ctx.arc(radarX, radarY, 15, 0, Math.PI * 2);
                ctx.fill();
                
                // Draw legend
                ctx.fillStyle = '#28a745';
                ctx.fillRect(20, 20, 15, 15);
                ctx.fillStyle = '#000';
                ctx.font = '12px Arial';
                ctx.fillText('Start', 40, 30);
                
                ctx.fillStyle = '#dc3545';
                ctx.fillRect(20, 40, 15, 15);
                ctx.fillStyle = '#000';
                ctx.fillText('End', 40, 50);
                
                ctx.fillStyle = color;
                ctx.fillRect(20, 60, 15, 15);
                ctx.fillStyle = '#000';
                ctx.fillText('Path', 40, 70);
            }
            
            // Update target counts every 3 seconds
            setInterval(updateTargetCounts, 2000);
            updateTargetCounts();
        });
    </script>
</body>
</html>
""")

# shutdown
with open('templates/shutdown.html', 'w', encoding='utf-8') as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>System Shutdown</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-dark text-light">
    <div class="container vh-100 d-flex flex-column justify-content-center align-items-center">
        <h1 class="display-1"><i class="fa-solid fa-power-off"></i></h1>
        <h1 class="display-4">System Shutdown</h1>
        <p class="lead">The radar system has been powered down.</p>
        <div class="mt-4">
            <button class="btn btn-outline-light" onclick="location.reload()">
                <i class="fa-solid fa-rotate"></i> Check System Status
            </button>
        </div>
    </div>
</body>
</html>
""")

# ==========================================
# Main Execution
# ==========================================

if __name__ == '__main__':
    # Start web server
    app.run(host='0.0.0.0', port=5000, debug=True)