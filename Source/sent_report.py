import smtplib
import schedule
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd
import json
import os

# Define paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STUDENTS_DATA_FILE = os.path.join(BASE_DIR, "students_data.csv")
ATTENDANCE_LOG_FILE = os.path.join(BASE_DIR, "attendance_log.csv")
# Configuration
CLASS_NAME = "ECE-A"
ADVISOR_EMAIL = "mathir078@gmail.com"  # ✅ Replace with actual advisor email
SENDER_EMAIL = "smartattendance078@gmail.com"
SENDER_PASSWORD = "ukwk vrtu tomm hcrv"  # 🔐 Use Gmail App Password

# Load configuration from main app
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')

def load_config():
    try:
        with open(CONFIG_FILE) as f:
            config = json.load(f)
            return config.get('email_report', {})
    except Exception as e:
        print(f"Error loading config: {e}")
        return {'time': '16:30', 'days': [0,1,2,3,4]}

# Load email credentials securely
def get_email_creds():
    try:
        with open(os.path.join(BASE_DIR, 'email_cred.txt')) as f:
            return f.read().splitlines()
    except FileNotFoundError:
        print("Email credentials file not found!")
        return ["", ""]

EMAIL_ADDRESS, EMAIL_PASSWORD = get_email_creds()

# Update file paths to use relative paths
STUDENTS_DATA_FILE = os.path.join(BASE_DIR, "students_data.csv")
ATTENDANCE_LOG_FILE = os.path.join(BASE_DIR, "attendance_log.csv")

# Function to fetch today's present roll numbers
def get_present_rolls():
    if not os.path.exists(ATTENDANCE_LOG_FILE):
        print("[WARNING] 🚫 attendance_log.csv not found.")
        return []

    df = pd.read_csv(ATTENDANCE_LOG_FILE)

    today = datetime.now().strftime("%Y-%m-%d")
    today_df = df[df['timestamp'].str.startswith(today)]

    present_rolls = today_df[today_df['status'].str.strip().str.lower() == 'present']['roll'].unique().tolist()
    return present_rolls

# Function to send email to advisor
def send_advisor_email(present_students, absent_students):
    # Skip sending on Sundays
    if datetime.now().weekday() == 6:  # 6 = Sunday
        print("⏸️ Skipping advisor email: Today is Sunday")
        return

    now = datetime.now().strftime("%d-%m-%Y")
    subject = f"[{CLASS_NAME}] Attendance Report - {now}"
    body = f"Dear Sir/Madam,\n\nHere is the attendance report for {CLASS_NAME} on {now}:\n\n"
    body += f"✅ Present Students:\n{', '.join(map(str, present_students))}\n\n"
    body += f"❌ Absent Students:\n{', '.join(map(str, absent_students))}\n\n"
    body += "Regards,\nSmart Attendance System"

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = ADVISOR_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print(f"[{datetime.now()}] ✅ Email sent to advisor: {ADVISOR_EMAIL}")
    except Exception as e:
        print(f"[ERROR] ❌ Failed to send email to advisor: {e}")

# Function to send emails to absentees' parents
def send_absentee_emails(absent_students):
    # Skip sending on Sundays
    if datetime.now().weekday() == 6:  # 6 = Sunday
        print("⏸️ Skipping parent notifications: Today is Sunday")
        return

    if not os.path.exists(STUDENTS_DATA_FILE):
        print("[WARNING] 🚫 students_data.csv not found.")
        return

    students_df = pd.read_csv(STUDENTS_DATA_FILE)
    absentees_df = students_df[students_df['roll'].isin(absent_students)]

    for _, row in absentees_df.iterrows():
        roll = row['roll']
        name = row['name']
        parent_email = row['parent_email']

        subject = f"🚨 Absence Notification for {name} (Roll: {roll})"
        body = f"""
Dear Parent,

This is to inform you that your ward, {name} (Roll Number: {roll}), was marked absent today ({datetime.now().strftime("%d-%m-%Y")}) during attendance.

If you believe this is a mistake, please reach out to the class teacher.

Best regards,  
Smart Attendance System
"""

        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = parent_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        try:
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.send_message(msg)
            print(f"[✅] Email sent to parent: {parent_email} for {name}")
        except Exception as e:
            print(f"[❌] Failed to send email to parent: {parent_email}: {e}")

# Main function to send all emails
def send_emails():
    present_students = get_present_rolls()

    if not os.path.exists(STUDENTS_DATA_FILE):
        print("[WARNING] 🚫 students_data.csv not found.")
        return

    students_df = pd.read_csv(STUDENTS_DATA_FILE)
    all_students = students_df['roll'].tolist()
    absent_students = list(set(all_students) - set(present_students))

    print(f"[INFO] ✅ Present Students: {present_students}")
    print(f"[INFO] ❌ Absent Students: {absent_students}")

    # Send email to advisor
    send_advisor_email(present_students, absent_students)

    # Send emails to absentees' parents
    send_absentee_emails(absent_students)

# Schedule the email sending at 4:00 PM daily
#schedule.every().day.at(send_time).do(send_emails)
print(f"📨 Email sender running...")
send_emails()
time.sleep(30)
exit()
while True:
    schedule.run_pending()
    time.sleep(30)


def send_monthly_absence_report():
    if not os.path.exists(ATTENDANCE_LOG_FILE) or not os.path.exists(STUDENTS_DATA_FILE):
        print("[WARNING] 🚫 Required files not found.")
        return

    # Get current month and year
    now = datetime.now()
    month_str = now.strftime("%Y-%m")
    month_name = now.strftime("%B %Y")

    # Read attendance log
    df = pd.read_csv(ATTENDANCE_LOG_FILE)
    # Filter for current month
    month_df = df[df['timestamp'].str.startswith(month_str)]

    # Count absences per student
    absence_counts = month_df[month_df['status'].str.strip().str.lower() != 'present'].groupby('roll').size().to_dict()

    # Read student data
    students_df = pd.read_csv(STUDENTS_DATA_FILE)

    for _, row in students_df.iterrows():
        roll = row['roll']
        name = row['name']
        parent_email = row['parent_email']
        absences = absence_counts.get(roll, 0)

        subject = f"Monthly Attendance Report for {name} (Roll: {roll}) - {month_name}"
        body = f"""
Dear Parent,

Here is the attendance summary for your ward, {name} (Roll Number: {roll}), for {month_name}:

Total sessions absent: {absences}

Please encourage regular attendance for better academic performance.

Best regards,
Smart Attendance System
"""

        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = parent_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        try:
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.send_message(msg)
            print(f"[✅] Monthly report sent to parent: {parent_email} for {name}")
        except Exception as e:
            print(f"[❌] Failed to send monthly report to parent: {parent_email}: {e}")

# Schedule the monthly report to run at 23:59 on the last day of the month
def schedule_monthly_report():
    # Find last day of the current month
    from calendar import monthrange
    now = datetime.now()
    last_day = monthrange(now.year, now.month)[1]
    run_time = f"{last_day:02d}-" + now.strftime("%m-%Y") + " 23:59"
    # For schedule, use day and time only
    schedule.every().month.at("23:59").do(send_monthly_absence_report)

# Example: To run monthly report manually for testing
# send_monthly_absence_report()

# To schedule monthly report (uncomment if you want to use schedule)
# schedule_monthly_report()


# Replace the schedule setup
config = load_config()
report_config = config.get('email_report', {})
report_time = report_config.get('time', '16:30')
report_days = report_config.get('days', [0,1,2,3,4])  # 0=Monday, 6=Sunday

# Map day numbers to schedule
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
        day_map[day].at(report_time).do(send_emails)
    else:
        print(f"Invalid day number in config: {day}")


def send_email(recipient, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, recipient, msg.as_string())
        print(f"Email sent to {recipient}")
        return True
    except Exception as e:
        print(f"Failed to send email to {recipient}: {str(e)}")
        return False