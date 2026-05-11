import warnings
warnings.filterwarnings('ignore', category=UserWarning, message='pkg_resources is deprecated')

import os
import cv2
import base64
import datetime
import numpy as np
import pandas as pd
import face_recognition
import csv
import threading
import time
import schedule
import logging
import subprocess
import json
import shutil
from flask import Flask, render_template, request, redirect, url_for, send_file, session, jsonify
from werkzeug.utils import secure_filename
from functools import wraps
import geopy.distance
from dotenv import load_dotenv

# --- Initial Configuration ---
load_dotenv()

# Use relative paths for portability
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')
STUDENTS_DATASET = os.path.join(BASE_DIR, "students_dataset")
ATTENDANCE_LOG = os.path.join(BASE_DIR, "attendance_log.csv")
STUDENTS_DATA_FILE = os.path.join(BASE_DIR, "students_data.csv")
LOG_FILE = os.path.join(BASE_DIR, "app.log")
SENT_REPORT_SCRIPT = os.path.join(BASE_DIR, "sent_report.py")

os.makedirs(STUDENTS_DATASET, exist_ok=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration Helper Functions ---
def load_config():
    """Loads settings from config.json"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.critical(f"CRITICAL: config.json not found at {CONFIG_FILE}! Please create it.")
        exit("Error: config.json not found.")
    except json.JSONDecodeError:
        logging.critical(f"CRITICAL: {CONFIG_FILE} is not valid JSON!")
        exit("Error: Could not parse config.json.")

def save_config(config_data):
    """Saves settings to config.json"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f, indent=2)

# Load initial config at startup
CONFIG = load_config()

# --- Flask App Initialization ---
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'a_default_fallback_secret_key')
app.config.update(
    PERMANENT_SESSION_LIFETIME=datetime.timedelta(minutes=30)
)


# --- Helper Functions & Decorators ---

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            app.logger.warning(f"Unauthorized access attempt to admin route: {request.path}")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('student_roll'):
            return redirect(url_for('student_login'))
        return f(*args, **kwargs)
    return decorated_function
    
def get_current_session():
    now = datetime.datetime.now()
    for session_name, hour in CONFIG.get('session_times', []):
        if now.hour == hour:
            return session_name
    return None

def validate_geolocation(submitted_gps):
    try:
        lat, lon = map(float, submitted_gps.split(','))
        campus_lat, campus_lon = CONFIG.get('campus_geofence', [0, 0])
        allowed_radius = CONFIG.get('allowed_radius', 500)
        distance = geopy.distance.distance((lat, lon), (campus_lat, campus_lon)).m
        return distance <= allowed_radius
    except (ValueError, TypeError):
        return False

# --- Core Attendance Logic ---

def log_attendance(roll, session_name, gps):
    """Logs attendance if not already logged for the session."""
    if not validate_geolocation(gps):
        app.logger.warning(f"Geolocation validation failed for Roll: {roll} at GPS: {gps}")
        return False, "Geolocation is outside the allowed campus area."

    today_date = datetime.date.today().strftime("%Y-%m-%d")
    
    if os.path.exists(ATTENDANCE_LOG):
        df = pd.read_csv(ATTENDANCE_LOG, dtype={'roll': str})
        already_logged = not df[(df['roll'] == str(roll)) & 
                                (df['session'] == session_name) & 
                                (df['timestamp'].str.startswith(today_date))].empty
        if already_logged:
            app.logger.info(f"Attendance already marked for Roll: {roll} in Session: {session_name}")
            return False, f"Attendance already marked for {roll} in {session_name}."
    
    try:
        with open(ATTENDANCE_LOG, 'a', newline='') as csvfile:
            fieldnames = ['roll', 'timestamp', 'session', 'gps', 'status']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if csvfile.tell() == 0:
                writer.writeheader()
            writer.writerow({
                'roll': roll,
                'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'session': session_name,
                'gps': gps,
                'status': 'Present'
            })
        app.logger.info(f"Successfully logged attendance for Roll: {roll} in Session: {session_name}")
        return True, f"Attendance marked for Roll: {roll} in {session_name}."
    except IOError as e:
        app.logger.error(f"Error writing to attendance log: {e}")
        return False, "Server error while logging attendance."

def process_face_attendance(data):
    """Processes attendance via facial recognition."""
    roll, gps, img_data = data['roll'], data['gps'], data['image']
    current_session = get_current_session()
    if not current_session:
        return jsonify({"error": "Not within any designated session time."}), 400

    try:
        img_bytes = base64.b64decode(img_data.split(',')[1])
        image = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        submitted_encodings = face_recognition.face_encodings(image)
        
        if not submitted_encodings:
            return jsonify({"error": "No face detected in the submitted image."}), 400
        
        student_dir = os.path.join(STUDENTS_DATASET, roll)
        if not os.path.isdir(student_dir):
            return jsonify({"error": "Roll number not found in dataset."}), 404

        known_encodings = []
        for file_name in os.listdir(student_dir):
            known_image = face_recognition.load_image_file(os.path.join(student_dir, file_name))
            known_encs = face_recognition.face_encodings(known_image)
            if known_encs:
                known_encodings.append(known_encs[0])

        if not known_encodings:
            return jsonify({"error": "No reference images found for this roll number."}), 404

        matches = face_recognition.compare_faces(known_encodings, submitted_encodings[0])
        if any(matches):
            success, message = log_attendance(roll, current_session, gps)
            return jsonify({"message": message}), 200
        else:
            return jsonify({"error": "Face mismatch. Authentication failed."}), 403

    except Exception as e:
        app.logger.error(f"Face processing error for roll {roll}: {e}")
        return jsonify({"error": "An internal error occurred."}), 500

def process_qr_attendance(data):
    """Processes attendance via QR code."""
    qr_data = data.get('qr_code')
    try:
        roll, gps = qr_data.split('|')
        current_session = get_current_session()
        if not current_session:
            return jsonify({"error": "Not within any designated session time."}), 400

        if not os.path.isdir(os.path.join(STUDENTS_DATASET, roll)):
            return jsonify({"error": "Invalid Roll Number in QR Code."}), 404

        success, message = log_attendance(roll, current_session, gps)
        return jsonify({"message": message}), 200

    except Exception as e:
        app.logger.error(f"QR processing error: {e}")
        return jsonify({"error": "Invalid QR code format."}), 400

# --- Scheduler Setup ---

def run_daily_report_script():
    """Executes the external script to send email reports."""
    app.logger.info("Scheduler triggered: Executing daily report script...")
    try:
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        result = subprocess.run(
            ['python', SENT_REPORT_SCRIPT],
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',  # Add explicit encoding
            errors='ignore',   # Add error handling
            env=env
        )
        app.logger.info("Daily report script executed successfully.")
        if result.stdout:
            app.logger.info(f"Report script output:\n{result.stdout}")
    except FileNotFoundError:
        app.logger.error(f"Failed to execute report script: '{SENT_REPORT_SCRIPT}' not found.")
    except subprocess.CalledProcessError as e:
        app.logger.error(f"Daily report script failed with exit code {e.returncode}.")
        if e.stderr:
            app.logger.error(f"Report script error output:\n{e.stderr}")
    except Exception as e:
        app.logger.error(f"An unexpected error occurred while running report script: {e}")

# Replace the hardcoded schedule with config-based scheduling
def schedule_reports():
    schedule.clear('daily_reports')
    report_time = CONFIG.get('email_report', {}).get('time', '16:30')
    report_days = CONFIG.get('email_report', {}).get('days', [0,1,2,3,4])
    
    day_map = {
        0: schedule.every().monday,
        1: schedule.every().tuesday,
        2: schedule.every().wednesday,
        3: schedule.every().thursday,
        4: schedule.every().friday,
        5: schedule.every().saturday,
        6: schedule.every().sunday
    }
    
    for day in report_days:
        if 0 <= day <= 6:
            day_map[day].at(report_time).do(run_daily_report_script).tag('daily_reports')

schedule_reports()

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()
app.logger.info("Background scheduler started.")

# --- General & Student Routes ---

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/submit', methods=['POST'])
def submit():
    data = request.get_json()
    if not data:
        app.logger.warning("Submission received with invalid JSON payload.")
        return jsonify({"error": "Invalid JSON payload"}), 400
    
    if 'image' in data:
        app.logger.info(f"Processing FACE submission for Roll: {data.get('roll')}")
        return process_face_attendance(data)
    elif 'qr_code' in data:
        app.logger.info(f"Processing QR submission.")
        return process_qr_attendance(data)
    else:
        app.logger.warning("Submission received with an invalid method.")
        return jsonify({"error": "Invalid attendance method"}), 400

@app.route('/student/login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        roll_no = request.form.get('roll_no', '').strip()
        app.logger.info(f"Student login attempt for Roll: {roll_no}")
        if os.path.exists(STUDENTS_DATA_FILE):
            students_df = pd.read_csv(STUDENTS_DATA_FILE, dtype={'roll': str})
            if roll_no in students_df['roll'].values:
                app.logger.info(f"Student login successful for Roll: {roll_no}")
                session['student_roll'] = roll_no
                return redirect(url_for('student_dashboard'))
        app.logger.warning(f"Student login failed for Roll: {roll_no}")
        return render_template('student_login.html', error="Invalid Roll Number")
    return render_template('student_login.html')

@app.route('/student/dashboard')
@student_required
def student_dashboard():
    roll_no = session['student_roll']
    total_sessions_conducted = 0
    present_count = 0
    records = []

    if os.path.exists(ATTENDANCE_LOG):
        att_df = pd.read_csv(ATTENDANCE_LOG, dtype={'roll': str})
        total_days = len(pd.to_datetime(att_df['timestamp']).dt.date.unique())
        total_sessions_conducted = total_days * len(CONFIG['session_times'])
        
        student_att = att_df[att_df['roll'] == roll_no]
        present_count = len(student_att)
        records = student_att.to_dict('records')
    
    attendance_percentage = (present_count / total_sessions_conducted * 100) if total_sessions_conducted > 0 else 0
        
    return render_template('student_dashboard.html', 
                           roll_no=roll_no,
                           present_count=present_count,
                           attendance_percentage=f"{attendance_percentage:.2f}",
                           records=records)

@app.route('/student/logout')
def student_logout():
    roll_no = session.pop('student_roll', None)
    app.logger.info(f"Student {roll_no} logged out.")
    return redirect(url_for('student_login'))

# --- Admin Routes ---

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        app.logger.info(f"Admin login attempt from IP: {request.remote_addr}")
        username = request.form.get('username')
        password = request.form.get('password')
        app.logger.info(f"Submitted Username: '{username}'")
        app.logger.info(f"Expected Username:  '{CONFIG['admin_username']}'")
        if username == CONFIG['admin_username'] and password == CONFIG['admin_password']:
            app.logger.info(f"Credentials for '{username}' VERIFIED. Logging in.")
            session['admin_logged_in'] = True
            return redirect(url_for('admin_panel'))
        else:
            app.logger.warning(f"Credentials for '{username}' MISMATCHED. Returning to login page.")
            return render_template('admin_login.html', error="Invalid username or password.")
    return render_template('admin_login.html')

@app.route('/admin/logout')
@admin_required
def admin_logout():
    session.pop('admin_logged_in', None)
    app.logger.info("Admin user logged out.")
    return redirect(url_for('admin_login'))

@app.route('/admin/panel')
@admin_required
def admin_panel():
    stats = {'total_students': 0, 'present_today': 0, 'absent_today': 0, 'attendance_rate': 0.0}
    if os.path.exists(STUDENTS_DATA_FILE):
        try:
            students_df = pd.read_csv(STUDENTS_DATA_FILE)
            stats['total_students'] = len(students_df)
        except pd.errors.EmptyDataError:
            stats['total_students'] = 0
    if os.path.exists(ATTENDANCE_LOG):
        try:
            att_df = pd.read_csv(ATTENDANCE_LOG)
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            att_df['timestamp'] = att_df['timestamp'].astype(str)
            today_att_df = att_df[att_df['timestamp'].str.startswith(today_str)]
            present_rolls = today_att_df['roll'].unique()
            stats['present_today'] = len(present_rolls)
            if stats['total_students'] > 0:
                stats['absent_today'] = stats['total_students'] - stats['present_today']
                stats['attendance_rate'] = (stats['present_today'] / stats['total_students']) * 100
        except pd.errors.EmptyDataError:
            pass
    return render_template('admin_panel.html', stats=stats)

@app.route('/admin/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    if request.method == 'POST':
        app.logger.info("Admin is updating application settings.")
        current_config = load_config()
        current_config['admin_username'] = request.form.get('admin_username')
        current_config['admin_password'] = request.form.get('admin_password')
        current_config['allowed_radius'] = int(request.form.get('allowed_radius'))
        lat = float(request.form.get('geo_lat'))
        lon = float(request.form.get('geo_lon'))
        current_config['campus_geofence'] = [lat, lon]
        new_sessions = []
        session_names = request.form.getlist('session_name[]')
        session_hours = request.form.getlist('session_hour[]')
        for name, hour in zip(session_names, session_hours):
            if name and hour:
                new_sessions.append([name, int(hour)])
        current_config['session_times'] = new_sessions
        # Add email scheduling configuration
        current_config['email_report'] = {
            'time': request.form.get('report_time'),
            'days': list(map(int, request.form.getlist('report_days[]')))
        }
        
        save_config(current_config)
        return render_template('settings.html', 
                             config=current_config,
                             success_message="Settings saved! Please restart the server for changes to take effect.")
    
    current_config = load_config()
    # Initialize default values if not exists
    if 'email_report' not in current_config:
        current_config['email_report'] = {'time': '16:30', 'days': [0,1,2,3,4]}
    return render_template('settings.html', config=current_config)

@app.route('/admin/register', methods=['GET', 'POST'])
@admin_required
def register_student():
    if request.method == 'POST':
        try:
            roll_no = request.form['roll_no'].strip()
            student_name = request.form['student_name'].strip()
            parent_email = request.form['parent_email'].strip()
            selfie = request.files.get('selfie')

            app.logger.info(f"Attempting to register new student with Roll: {roll_no}")
            if not all([roll_no, student_name, parent_email, selfie]):
                 return render_template('register_student.html', error="All fields are required.")

            student_folder = os.path.join(STUDENTS_DATASET, roll_no)
            os.makedirs(student_folder, exist_ok=True)
            selfie.save(os.path.join(student_folder, "img1.jpg"))

            df = pd.read_csv(STUDENTS_DATA_FILE) if os.path.exists(STUDENTS_DATA_FILE) else pd.DataFrame(columns=['roll', 'name', 'parent_email'])
            df = df[df['roll'].astype(str) != roll_no]
            new_student = pd.DataFrame([{'roll': roll_no, 'name': student_name, 'parent_email': parent_email}])
            df = pd.concat([df, new_student], ignore_index=True)
            df.to_csv(STUDENTS_DATA_FILE, index=False)
            
            app.logger.info(f"Successfully registered student with Roll: {roll_no}")
            return render_template('register_student.html', success="Student registered successfully!")
        except Exception as e:
            app.logger.error(f"Error during student registration: {e}")
            return render_template('register_student.html', error=f"An error occurred: {e}")
            
    return render_template('register_student.html')

@app.route('/admin/remove_student', methods=['GET', 'POST'])
@admin_required
def remove_student():
    if request.method == 'POST':
        roll_no = request.form.get('roll_no', '').strip()
        app.logger.info(f"Attempting to remove student with Roll: {roll_no}")
        if not roll_no:
            return render_template('remove_student.html', error="Roll number is required.")
        try:
            if os.path.exists(STUDENTS_DATA_FILE):
                df = pd.read_csv(STUDENTS_DATA_FILE, dtype={'roll': str})
                if df[df['roll'] == roll_no].empty:
                    return render_template('remove_student.html', error=f"Roll number {roll_no} not found.")
                df = df[df['roll'] != roll_no]
                df.to_csv(STUDENTS_DATA_FILE, index=False)

            student_folder = os.path.join(STUDENTS_DATASET, roll_no)
            if os.path.isdir(student_folder):
                shutil.rmtree(student_folder)

            if os.path.exists(ATTENDANCE_LOG):
                df_att = pd.read_csv(ATTENDANCE_LOG, dtype={'roll': str})
                df_att = df_att[df_att['roll'] != roll_no]
                df_att.to_csv(ATTENDANCE_LOG, index=False)

            app.logger.info(f"Successfully removed student with Roll: {roll_no}")
            return render_template('remove_student.html', success=f"Student {roll_no} and all associated data have been removed.")
        except Exception as e:
            app.logger.error(f"Error removing student {roll_no}: {e}")
            return render_template('remove_student.html', error=f"An error occurred: {e}")
    
    return render_template('remove_student.html')

@app.route('/admin/view_attendance')
@admin_required
def view_attendance():
    if not os.path.isfile(ATTENDANCE_LOG):
        return render_template('view_attendance.html', attendance_table="<p>No attendance records found.</p>")
    df = pd.read_csv(ATTENDANCE_LOG)
    attendance_html = df.to_html(classes='table table-striped table-hover', index=False)
    return render_template('view_attendance.html', attendance_table=attendance_html)

@app.route('/admin/download')
@admin_required
def download_attendance():
    return send_file(ATTENDANCE_LOG, as_attachment=True, download_name='attendance_log.csv')

@app.route('/admin/analytics')
@admin_required
def attendance_analytics():
    app.logger.info("Admin accessing attendance analytics page.")
    if not os.path.exists(STUDENTS_DATA_FILE) or not os.path.exists(ATTENDANCE_LOG):
        app.logger.warning("Analytics attempted but data files are missing.")
        return render_template('analytics.html', analytics_data=None, error="Student data or attendance log not found.")
        
    try:
        students_df = pd.read_csv(STUDENTS_DATA_FILE, dtype={'roll': str})
        att_df = pd.read_csv(ATTENDANCE_LOG, dtype={'roll': str})

        if att_df.empty:
            return render_template('analytics.html', analytics_data=[], error="Attendance log is empty.")

        total_days = len(pd.to_datetime(att_df['timestamp']).dt.date.unique())
        total_sessions_conducted = total_days * len(CONFIG['session_times'])
        
        analytics = []
        for _, student in students_df.iterrows():
            roll = student['roll']
            student_records = att_df[att_df['roll'] == roll]
            present_count = len(student_records)
            percentage = (present_count / total_sessions_conducted * 100) if total_sessions_conducted > 0 else 0
            analytics.append({
                'roll': roll,
                'name': student['name'],
                'present_count': present_count,
                'percentage': f"{percentage:.2f}",
                'at_risk': percentage < 75.0
            })
        return render_template('analytics.html', analytics_data=analytics)
    except Exception as e:
        app.logger.error(f"Error generating analytics: {e}")
        return render_template('analytics.html', analytics_data=None, error="An error occurred while generating the report.")


# --- Main Execution Block ---
if __name__ == '__main__':
    app.logger.info("Starting Smart Attendance System server...")
    # This tells Flask to use your SSL certificate to enable HTTPS
    ssl_dir = os.path.join(BASE_DIR, 'SSL_keys')
    cert_path = os.path.join(ssl_dir, 'cert.pem')
    key_path = os.path.join(ssl_dir, 'key.pem')
    app.run(debug=True, host='0.0.0.0', port=5000, ssl_context=(cert_path, key_path))
