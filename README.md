# Attendance Management System

A desktop attendance application built with **Python, Tkinter and SQLite**.

## Features
- Add, edit, search and delete student records
- Mark attendance as Present, Absent or Late
- Store one attendance record per student per date (saving again updates it)
- Dashboard showing student count and today's attendance totals
- Date-range attendance report with attendance percentage
- Export reports to CSV
- SQLite database is created automatically as `attendance.db`

## Requirements
- Python 3.9 or newer
- Tkinter (included with most standard Python installations)
- No third-party Python packages are required

## Run on Windows
1. Install Python from https://www.python.org/downloads/
2. During installation, enable **Add Python to PATH**.
3. Extract this ZIP file.
4. Open the extracted folder.
5. Double-click `run.bat`, or open PowerShell in this folder and run:

   ```powershell
   python main.py
   ```

## Run on macOS / Linux
Open a terminal in the project folder and run:

```bash
python3 main.py
```

If Tkinter is missing on Linux, install your distribution's Tk package (for Ubuntu/Debian: `sudo apt install python3-tk`).

## Database
The application creates `attendance.db` in the same folder the first time it starts. It contains:
- `students`: roll number, name, course and semester
- `attendance`: student, date, status and remarks

Keep `attendance.db` safe: it contains your records. To back it up, close the application and copy the database file.

## Attendance percentage
`Present % = Present records / (Present + Absent + Late records) × 100`

Only dates with a saved attendance status are included in the denominator. "Not marked" is not counted.

## Project structure
```text
attendance_management_system/
├── main.py
├── attendance.db
├── README.md
├── requirements.txt
└── run.bat
```

## Notes
- Roll numbers must be unique.
- Dates must use `YYYY-MM-DD`, for example `2026-11-10`.
- Deleting a student also deletes their attendance records.
- This is a local desktop application; it does not include cloud sync or multi-user login.
