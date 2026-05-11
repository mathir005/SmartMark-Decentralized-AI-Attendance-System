# 🎓 Smart Attendance System v2

![Smart Attendance System](https://img.shields.io/badge/Smart%20Attendance-v2-brightgreen)
![Python](https://img.shields.io/badge/Python-3.7%2B-blue)
![Flask](https://img.shields.io/badge/Flask-Web%20App-orange)
![Face%20Recognition](https://img.shields.io/badge/Face%20Recognition-dlib%2Bface__recognition-purple)
![License](https://img.shields.io/badge/License-MIT-green)

A **web-based smart attendance management system** that eliminates the need for a single hardware camera. Every student can mark their own attendance simultaneously using their **mobile phone or laptop camera** through a local web page — powered by **real-time facial recognition** and **GPS geofencing**.

---

## 📌 Table of Contents

- [🌟 Features](#-features)
- [🏗️ Architecture](#-architecture)
- [🛠️ Prerequisites](#-prerequisites)
- [⚡ Quick Start](#-quick-start)
- [📂 Project Structure](#-project-structure)
- [🔧 Configuration](#-configuration)
- [🧑‍🎓 Student Workflow](#-student-workflow)
- [🛡️ Admin Panel](#-admin-panel)
- [📧 Email Notifications](#-email-notifications)
- [🔐 Security & Privacy](#-security--privacy)
- [🧪 Testing](#-testing)
- [📝 License](#-license)
- [👤 Authors](#-authors)

---

## 🌟 Features

| Feature | Description |
|---------|-------------|
| **Multi-device Attendance** | Students mark attendance from their own phones/laptops via a browser — no single hardware camera needed |
| **Real-time Face Recognition** | Uses `dlib` and `face_recognition` library for accurate facial matching |
| **GPS Geofencing** | Validates student location using GPS coordinates — attendance is only accepted within the campus radius (default: 500m) |
| **QR Code Attendance** | Alternative QR-based attendance method for quick check-ins |
| **Session-based Tracking** | Supports multiple sessions per day (e.g., Session 1 – 9 AM, Session 2 – 10 AM, etc.) |
| **Student Dashboard** | Students can log in with their roll number and view attendance history & percentage |
| **Admin Panel** | Full admin control — register students, remove students, view logs, analytics, and configure settings |
| **Email Notifications** | Daily automated emails to advisors with attendance summaries; absent students' parents are also notified |
| **Monthly Reports** | Monthly absence reports sent to parents via email |
| **Real-time Multi-user** | Multiple students can mark attendance simultaneously on their own devices |
| **Responsive Design** | Mobile-friendly web interface |

---

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  Student     │     │  Flask Web   │     │   Admin       │
│  Device      │────▶│  Server      │◀────│   Panel       │
│  (Camera +   │     │  (main.py)   │     │   (Dashboard) │
│   GPS)       │     │              │     │               │
└─────────────┘     └──────┬───────┘     └───────────────┘
                           │
                    ┌──────▼───────┐
                    │  Face        │
                    │  Recognition │
                    │  (dlib)      │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  students_   │
                    │  dataset/    │  ┌────────────┐
                    │  (face imgs) │  │ attendance │
                    └──────────────┘  │ _log.csv   │
                                      └────────────┘
```

### How It Works

1. **Student** opens the web page on their phone/laptop
2. The browser requests **camera access** and captures a live photo
3. The browser also fetches **GPS coordinates** from the device
4. Both image and GPS are sent to the **Flask server**
5. The server runs **facial recognition** against the student's stored face images
6. If the face matches AND the GPS is within campus bounds → **Attendance marked!**
7. Multiple students can do this **simultaneously** — no queue, no hardware bottleneck

---

## 🛠️ Prerequisites

- **Python 3.7+** (3.11+ recommended)
- **pip** (Python package manager)
- **A webcam** on any device (phone, laptop, tablet)
- **A browser** with camera & geolocation permissions (Chrome/Firefox/Edge)
- **dlib C++ library** (pre-built wheels included for Windows)

---

## ⚡ Quick Start

### Step 1: Install Dependencies

```bash
pip install -r Source/requirements.txt
```

> **Note:** If `face_recognition` or `dlib` fails to install, pre-built `.whl` files are included in the `dlib-python-main/` directory. Install them manually:
> ```bash
> pip install dlib-python-main/dlib-19.24.2-cp312-cp312-win_amd64.whl
> pip install face_recognition
> ```

### Step 2: Configure the System

Edit `Source/config.json` to set your campus coordinates, session times, and admin credentials:

```json
{
  "admin_username": "admin",
  "admin_password": "admin",
  "campus_geofence": [
    10.869828266872473,
    76.92645397136471
  ],
  "allowed_radius": 500,
  "session_times": [
    ["Session 1", 9],
    ["Session 2", 10],
    ["Session 3", 11],
    ["Session 4", 12],
    ["Session 5", 13],
    ["Session 6", 14],
    ["Session 7", 15]
  ],
  "email_report": {
    "time": "16:00",
    "days": [0, 1, 2, 3, 4]
  }
}
```

> **How to get campus coordinates:** Open Google Maps → right-click your campus → copy the latitude and longitude.

### Step 3: Register Students

1. Run the application (see Step 4)
2. Open `http://localhost:5000/admin` in browser
3. Login with admin credentials
4. Go to **"Register New Student"**
5. Enter **Roll Number**, **Name**, **Parent Email**
6. Upload a **clear selfie** of the student's face
7. Click **Register**

> Each student's face image is stored in `Source/students_dataset/{roll_number}/`

### Step 4: Run the Application

```bash
cd Source
python main.py
```

The server starts on **https://localhost:5000** (SSL enabled).

> **⚠️ HTTPS Required:** The browser's camera API only works over HTTPS or localhost. The project includes self-signed SSL certificates in `Source/SSL_keys/`. For production, use valid certificates via Let's Encrypt or similar.

### Step 5: Mark Attendance (Student Side)

1. Students open `https://localhost:5000` on their phone/laptop
2. They enter their **Roll Number**
3. The browser requests **camera** and **location** permissions
4. A live video feed appears from their device camera
5. Click **"📤 Submit Attendance"**
6. The system captures a photo → runs face recognition → validates GPS → marks attendance!

### Step 6: Monitor Attendance (Admin Side)

1. Go to `https://localhost:5000/admin`
2. Login as admin
3. View **Dashboard** with today's statistics (total students, present, absent, rate)
4. Access **all admin actions** from the dashboard:
   - **View Attendance Log** — raw table of all records
   - **Download CSV** — export attendance_log.csv
   - **Attendance Analytics** — per-student attendance %, at-risk flagging (<75%)
   - **Settings** — configure geofence, sessions, admin credentials, email
   - **Register/Remove Students** — manage student database

---

## 📂 Project Structure

```
Smart_Attendance_System2/
├── Source/
│   ├── main.py                  # Core Flask application & attendance logic
│   ├── sent_report.py           # Email sending script (daily + monthly reports)
│   ├── config.json              # Application configuration (geofence, sessions, etc.)
│   ├── students_data.csv        # Student records (roll, name, parent_email)
│   ├── attendance_log.csv       # Attendance records (roll, timestamp, session, gps, status)
│   ├── requirements.txt         # Python dependencies
│   ├── commands.txt             # Utility commands
│   ├── key.pem / cert.pem       # SSL certificate files
│   ├── app.log                  # Application log file
│   │
│   ├── students_dataset/        # Folder containing each student's face images
│   │   ├── 42/
│   │   │   └── img1.jpg         # Face photo of student with roll 42
│   │   └── 60/
│   │       └── img1.jpg         # Face photo of student with roll 60
│   │
│   ├── static/
│   │   └── script.js            # Client-side JavaScript for camera & geolocation
│   │
│   └── templates/               # HTML templates (Jinja2)
│       ├── index.html           # Main attendance page (camera capture)
│       ├── admin_panel.html     # Admin dashboard
│       ├── admin_login.html     # Admin login page
│       ├── student_login.html   # Student portal login
│       ├── student_dashboard.html # Student's own dashboard
│       ├── register_student.html # Register new student form
│       ├── remove_student.html   # Remove student form
│       ├── delete_student.html   # Delete student confirmation
│       ├── view_attendance.html  # Full attendance log table
│       ├── analytics.html       # Analytics page (per-student %)
│       ├── settings.html        # Application settings form
│       ├── layout.html          # Admin base template
│       └── layout_Student_portal.html # Student portal base template
│
├── dlib-python-main/            # Pre-built dlib wheels for Windows
├── logs/                        # Log directory
├── attendance_log.csv           # Duplicate attendance log (root level)
├── students_data.csv            # Duplicate student data (root level)
└── README.md                    # This file
```

---

## 🔧 Configuration

All settings are in `Source/config.json`:

| Setting | Description | Default |
|---------|-------------|---------|
| `admin_username` | Username for admin panel | `admin` |
| `admin_password` | Password for admin panel | `admin` |
| `campus_geofence` | `[latitude, longitude]` of campus center | `[10.87, 76.93]` |
| `allowed_radius` | Max distance (in meters) from campus for valid attendance | `500` |
| `session_times` | List of `[session_name, hour]` pairs | 7 sessions (9 AM – 3 PM) |
| `email_report.time` | Daily email report sending time | `16:00` |
| `email_report.days` | Days to send reports (0=Mon, 6=Sun) | `[0,1,2,3,4]` |

---

## 🧑‍🎓 Student Workflow

### Marking Attendance via Camera (Face Recognition)

1. Open browser (Chrome/Firefox/Edge) on phone or laptop
2. Go to `https://YOUR_SERVER_IP:5000`
3. Enter your **Roll Number**
4. Allow **camera** and **location** permissions when prompted
5. A live camera feed will appear
6. Click **"📤 Submit Attendance"**
7. The system:
   - Captures a snapshot from your camera
   - Extracts your GPS location
   - Verifies you are within the campus geofence (500m radius)
   - Compares your face with your registered photo using `face_recognition`
   - If everything checks out → ✅ **Attendance Marked Successfully!**
   - If face doesn't match → ❌ **Face mismatch. Authentication failed.**
   - If outside campus → ❌ **Geolocation is outside the allowed campus area.**

### Viewing Your Attendance

1. Go to `https://YOUR_SERVER_IP:5000/student/login`
2. Enter your Roll Number to log in
3. View your **dashboard** with:
   - Total sessions present
   - Overall attendance percentage
   - Full attendance log (date, session, status)

### QR Code Attendance (Alternative)

The system also supports QR code-based attendance if configured.

---

## 🛡️ Admin Panel

Access: `https://localhost:5000/admin`

| Action | Description |
|--------|-------------|
| **Dashboard** | View today's stats: total students, present, absent, attendance rate |
| **Register New Student** | Add a new student with roll number, name, parent email & face photo |
| **Remove Student** | Delete a student and all their associated data (photos, records) |
| **View Attendance Log** | See raw table of all attendance records |
| **Download CSV** | Export `attendance_log.csv` for external use |
| **Attendance Analytics** | Per-student attendance %, with "At Risk" flagging (<75%) |
| **Application Settings** | Configure geofence, session times, admin credentials, email reports |

---

## 📧 Email Notifications

The system automatically sends email reports:

### Daily Reports (Configurable)
- **To:** Class Advisor
- **Content:** Lists all present and absent students for the day
- **Timing:** Configured in settings (default: 4:00 PM, Monday–Friday)

### Absent Student Notifications
- **To:** Parents of absent students
- **Content:** Informs parents their ward was absent on that date
- **Sent:** Alongside daily reports

### Monthly Reports
- **To:** Parents of all students
- **Content:** Monthly absence summary per student
- **Timing:** Last day of each month at 11:59 PM

> **Gmail Setup Required:** Create an [App Password](https://myaccount.google.com/apppasswords) and update `SENDER_EMAIL` and `SENDER_PASSWORD` in `sent_report.py`

---

## 🔐 Security & Privacy

- **Face data is stored locally** — no cloud uploads; all facial encodings and images stay on your server
- **GPS geofencing** ensures attendance can only be marked within the campus
- **Session-based tracking** prevents duplicate attendance within the same session
- **Role-based access** — admin and student sessions are separated
- **Self-signed SSL** for HTTPS (replace with valid certificates for production)

---

## 🧪 Testing

The project includes test utilities in `Source/test files/`:

- `email_absentees.py` — Test the absentee email notification system
- `send_email_report.py` — Test the daily email report
- `daily_attendance.csv` — Sample attendance data for testing
- `mail_config.json` — Email configuration for testing

Run tests:
```bash
cd Source/test files
python email_absentees.py
python send_email_report.py
```

---

## 🚀 Future Enhancements

- [ ] Implement QR code attendance generation & scanning
- [ ] Add multi-factor authentication (face + password)
- [ ] Build a mobile app (React Native / Flutter) for offline caching
- [ ] Integrate with college ERP systems
- [ ] Add real-time WebSocket notifications
- [ ] Implement database migration to PostgreSQL/SQLite
- [ ] Add attendance prediction using ML models
- [ ] Support for multiple campus locations
- [ ] Add role-based access for faculty, HOD, and principal

---

## 📝 License

This project is licensed under the **MIT License** — see the LICENSE file for details.

---

## 👤 Authors

- **Mathiyarasu R** — Electronics Engineer, Embedded Systems Developer ([GitHub](https://github.com/mathir005))

---

## ⭐ Support

If you find this project useful, please consider giving it a ⭐ on GitHub! For issues, bugs, or feature requests, please open an [issue](https://github.com/your-repo/issues).

---

### 🔑 Key Differentiator

> **No single hardware camera needed!** Every student marks their own attendance from their **personal mobile device or laptop** through the same local webpage — making it scalable, cost-effective, and truly simultaneous for an entire classroom.
