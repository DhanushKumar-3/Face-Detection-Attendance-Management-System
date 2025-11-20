📘 Face Detection Attendance Management System

A Flask-based Face Detection Attendance System that marks attendance using real-time face recognition through a webcam. The system provides an Admin Panel, User Management, Attendance Logs, and Auto-Mark Attendance using advanced computer vision models.

🚀 Features
🔹 Face Recognition

Detect and recognize faces using OpenCV, dlib, and the face_recognition library.

🔹 Live Camera Attendance

Capture attendance through a live webcam feed.

🔹 User Registration

Add new users by registering their face data.

🔹 Multiple User Roles

Admin → Manage users, export logs, view reports

Student/User → Check attendance

🔹 Login System

Secure authentication for admin and users.

🔹 Attendance Logs

Store daily attendance records in a database.

🔹 CSV Export

Export attendance logs to .csv format.

🔹 Auto-Mark Attendance

Automatically detects the student and records attendance.

🔹 Flask Backend

Lightweight backend written in Python using Flask.

🔹 SQLite / MySQL Database

Supports both SQLite (default) and MySQL.

🔹 Logging System

Tracks system events and errors for debugging.

🛠️ Tech Stack
🔹 Backend

Python

Flask

🔹 Face Recognition

OpenCV

dlib

face_recognition

🔹 Frontend

HTML

CSS

JavaScript

🔹 Database

SQLite / MySQL

📂 Project Structure (Example)
Face-Detection-Attendance-Management-System/
│── app.py
│── requirements.txt
│── README.md
│── static/
│── templates/
│── models/
│── attendance_logs/
│── database/
└── utils/

⚙️ Installation & Setup
1️⃣ Clone the repository
git clone https://github.com/DhanushKumar-3/Face-Detection-Attendance-Management-System.git
cd Face-Detection-Attendance-Management-System

2️⃣ Create virtual environment
python -m venv venv
venv\Scripts\activate   # Windows

3️⃣ Install dependencies
pip install -r requirements.txt

4️⃣ Run the application
python app.py


Open your browser and visit:
👉 http://127.0.0.1:5000

📌 How It Works

Admin registers user face data

Camera captures face in real-time

Face encoding is compared with stored encodings

Attendance is automatically marked

Logs stored + export available

📤 Export Attendance

Admin can export attendance logs to a CSV file with one click.

🔐 User Roles
Admin

Add/Delete users

View attendance

Export logs

Manage database

Student/User

View personal attendance history

📝 License

This project is released under the MIT License.

⭐ Contribute

Pull requests are welcome!
Feel free to open issues for suggestions or bugs.
