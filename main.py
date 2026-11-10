"""
Attendance Management System
Python + Tkinter + SQLite
Run: python main.py
"""
import csv
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date, datetime
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "attendance.db"


class AttendanceDB:
    def __init__(self, path=DB_PATH):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_tables()

    def create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roll_no TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                course TEXT DEFAULT '',
                semester TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                attendance_date TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('Present', 'Absent', 'Late')),
                remarks TEXT DEFAULT '',
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
                UNIQUE(student_id, attendance_date)
            );
        """)
        self.conn.commit()

    def add_student(self, roll, name, course, semester):
        self.conn.execute(
            "INSERT INTO students(roll_no,name,course,semester) VALUES(?,?,?,?)",
            (roll.strip(), name.strip(), course.strip(), semester.strip()))
        self.conn.commit()

    def update_student(self, student_id, roll, name, course, semester):
        self.conn.execute(
            "UPDATE students SET roll_no=?,name=?,course=?,semester=? WHERE id=?",
            (roll.strip(), name.strip(), course.strip(), semester.strip(), student_id))
        self.conn.commit()

    def delete_student(self, student_id):
        self.conn.execute("DELETE FROM students WHERE id=?", (student_id,))
        self.conn.commit()

    def students(self, search=""):
        term = f"%{search.strip()}%"
        return self.conn.execute("""
            SELECT * FROM students
            WHERE roll_no LIKE ? OR name LIKE ? OR course LIKE ?
            ORDER BY roll_no COLLATE NOCASE
        """, (term, term, term)).fetchall()

    def save_attendance(self, student_id, day, status, remarks=""):
        self.conn.execute("""
            INSERT INTO attendance(student_id,attendance_date,status,remarks)
            VALUES(?,?,?,?)
            ON CONFLICT(student_id,attendance_date)
            DO UPDATE SET status=excluded.status, remarks=excluded.remarks
        """, (student_id, day, status, remarks.strip()))
        self.conn.commit()

    def attendance_for_day(self, day):
        return self.conn.execute("""
            SELECT s.id, s.roll_no, s.name,
                   COALESCE(a.status, 'Not marked') AS status,
                   COALESCE(a.remarks, '') AS remarks
            FROM students s
            LEFT JOIN attendance a
              ON a.student_id=s.id AND a.attendance_date=?
            ORDER BY s.roll_no COLLATE NOCASE
        """, (day,)).fetchall()

    def report(self, start, end):
        return self.conn.execute("""
            SELECT s.roll_no, s.name, s.course, s.semester,
                   SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) AS present,
                   SUM(CASE WHEN a.status='Absent' THEN 1 ELSE 0 END) AS absent,
                   SUM(CASE WHEN a.status='Late' THEN 1 ELSE 0 END) AS late,
                   COUNT(a.id) AS marked
            FROM students s
            LEFT JOIN attendance a
              ON a.student_id=s.id AND a.attendance_date BETWEEN ? AND ?
            GROUP BY s.id
            ORDER BY s.roll_no COLLATE NOCASE
        """, (start, end)).fetchall()

    def summary(self):
        total = self.conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        today = date.today().isoformat()
        rows = self.conn.execute(
            "SELECT status, COUNT(*) n FROM attendance WHERE attendance_date=? GROUP BY status",
            (today,)).fetchall()
        counts = {r["status"]: r["n"] for r in rows}
        return total, counts.get("Present", 0), counts.get("Absent", 0), counts.get("Late", 0)

    def close(self):
        self.conn.close()


class AttendanceApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Attendance Management System")
        self.geometry("1050x700")
        self.minsize(900, 600)
        self.db = AttendanceDB()
        self.selected_student_id = None
        self.configure(padx=12, pady=12)
        self.build_ui()
        self.refresh_all()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_ui(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 12))
        ttk.Label(header, text="ATTENDANCE MANAGEMENT SYSTEM",
                  font=("Segoe UI", 18, "bold")).pack(side="left")
        ttk.Label(header, text="Python • Tkinter • SQLite",
                  font=("Segoe UI", 9)).pack(side="right")

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True)

        self.dashboard_tab = ttk.Frame(self.tabs, padding=14)
        self.students_tab = ttk.Frame(self.tabs, padding=14)
        self.mark_tab = ttk.Frame(self.tabs, padding=14)
        self.report_tab = ttk.Frame(self.tabs, padding=14)
        self.tabs.add(self.dashboard_tab, text="Dashboard")
        self.tabs.add(self.students_tab, text="Students")
        self.tabs.add(self.mark_tab, text="Mark Attendance")
        self.tabs.add(self.report_tab, text="Reports")

        self.build_dashboard()
        self.build_students()
        self.build_mark_attendance()
        self.build_reports()

    def build_dashboard(self):
        ttk.Label(self.dashboard_tab, text="Today's Overview",
                  font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 4))
        self.today_label = ttk.Label(self.dashboard_tab, text="")
        self.today_label.pack(anchor="w", pady=(0, 16))
        cards = ttk.Frame(self.dashboard_tab)
        cards.pack(fill="x")
        self.stat_vars = [tk.StringVar(value="0") for _ in range(4)]
        labels = ["Total students", "Present today", "Absent today", "Late today"]
        for i, label in enumerate(labels):
            card = ttk.LabelFrame(cards, text=label, padding=18)
            card.grid(row=0, column=i, padx=6, sticky="nsew")
            ttk.Label(card, textvariable=self.stat_vars[i],
                      font=("Segoe UI", 24, "bold")).pack()
            cards.columnconfigure(i, weight=1)
        ttk.Label(self.dashboard_tab,
                  text="Use the Students tab to register students, Mark Attendance to record daily status, "
                       "and Reports to calculate attendance over a date range.",
                  wraplength=800, justify="left").pack(anchor="w", pady=28)
        ttk.Button(self.dashboard_tab, text="Refresh dashboard",
                   command=self.refresh_dashboard).pack(anchor="w")

    def build_students(self):
        form = ttk.LabelFrame(self.students_tab, text="Student details", padding=10)
        form.pack(fill="x")
        self.roll_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.course_var = tk.StringVar()
        self.sem_var = tk.StringVar()
        fields = [("Roll number *", self.roll_var), ("Student name *", self.name_var),
                  ("Course", self.course_var), ("Semester", self.sem_var)]
        for i, (label, var) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=0, column=i, sticky="w", padx=5)
            ttk.Entry(form, textvariable=var, width=24).grid(row=1, column=i, padx=5, pady=5, sticky="ew")
            form.columnconfigure(i, weight=1)
        buttons = ttk.Frame(form)
        buttons.grid(row=2, column=0, columnspan=4, sticky="w", padx=5, pady=5)
        ttk.Button(buttons, text="Add student", command=self.add_student).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="Update selected", command=self.update_student).pack(side="left", padx=6)
        ttk.Button(buttons, text="Delete selected", command=self.delete_student).pack(side="left", padx=6)
        ttk.Button(buttons, text="Clear", command=self.clear_student_form).pack(side="left", padx=6)

        searchrow = ttk.Frame(self.students_tab)
        searchrow.pack(fill="x", pady=10)
        ttk.Label(searchrow, text="Search:").pack(side="left")
        self.student_search = tk.StringVar()
        entry = ttk.Entry(searchrow, textvariable=self.student_search, width=35)
        entry.pack(side="left", padx=8)
        entry.bind("<KeyRelease>", lambda _e: self.refresh_students())
        ttk.Button(searchrow, text="Refresh", command=self.refresh_students).pack(side="left")

        columns = ("id", "roll", "name", "course", "semester")
        self.student_tree = ttk.Treeview(self.students_tab, columns=columns, show="headings", height=15)
        for col, title, width in [
            ("id", "ID", 55), ("roll", "Roll number", 150), ("name", "Student name", 280),
            ("course", "Course", 220), ("semester", "Semester", 120)]:
            self.student_tree.heading(col, text=title)
            self.student_tree.column(col, width=width, anchor="w")
        self.student_tree.pack(fill="both", expand=True)
        self.student_tree.bind("<<TreeviewSelect>>", self.on_student_select)

    def build_mark_attendance(self):
        top = ttk.Frame(self.mark_tab)
        top.pack(fill="x", pady=(0, 10))
        ttk.Label(top, text="Attendance date (YYYY-MM-DD):").pack(side="left")
        self.att_date_var = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(top, textvariable=self.att_date_var, width=15).pack(side="left", padx=8)
        ttk.Button(top, text="Load students", command=self.refresh_attendance).pack(side="left")
        ttk.Label(top, text="Select a student row, choose status, then save.").pack(side="right")

        columns = ("id", "roll", "name", "status", "remarks")
        self.att_tree = ttk.Treeview(self.mark_tab, columns=columns, show="headings", height=17)
        for col, title, width in [
            ("id", "ID", 55), ("roll", "Roll number", 140), ("name", "Student name", 280),
            ("status", "Current status", 140), ("remarks", "Remarks", 260)]:
            self.att_tree.heading(col, text=title)
            self.att_tree.column(col, width=width, anchor="w")
        self.att_tree.pack(fill="both", expand=True)
        self.att_tree.bind("<<TreeviewSelect>>", self.on_attendance_select)

        controls = ttk.LabelFrame(self.mark_tab, text="Update selected student's attendance", padding=10)
        controls.pack(fill="x", pady=10)
        self.att_status_var = tk.StringVar(value="Present")
        self.att_remarks_var = tk.StringVar()
        ttk.Label(controls, text="Status:").pack(side="left")
        ttk.Combobox(controls, textvariable=self.att_status_var,
                     values=["Present", "Absent", "Late"], state="readonly", width=14).pack(side="left", padx=8)
        ttk.Label(controls, text="Remarks:").pack(side="left")
        ttk.Entry(controls, textvariable=self.att_remarks_var, width=45).pack(side="left", padx=8)
        ttk.Button(controls, text="Save attendance", command=self.save_attendance).pack(side="left", padx=8)

    def build_reports(self):
        filters = ttk.LabelFrame(self.report_tab, text="Report date range", padding=10)
        filters.pack(fill="x")
        self.start_var = tk.StringVar(value=date.today().replace(day=1).isoformat())
        self.end_var = tk.StringVar(value=date.today().isoformat())
        ttk.Label(filters, text="From (YYYY-MM-DD):").pack(side="left")
        ttk.Entry(filters, textvariable=self.start_var, width=14).pack(side="left", padx=6)
        ttk.Label(filters, text="To:").pack(side="left")
        ttk.Entry(filters, textvariable=self.end_var, width=14).pack(side="left", padx=6)
        ttk.Button(filters, text="Generate report", command=self.generate_report).pack(side="left", padx=6)
        ttk.Button(filters, text="Export CSV", command=self.export_report).pack(side="left", padx=6)

        cols = ("roll", "name", "course", "semester", "present", "absent", "late", "marked", "percent")
        self.report_tree = ttk.Treeview(self.report_tab, columns=cols, show="headings", height=17)
        headers = [
            ("roll", "Roll no.", 100), ("name", "Name", 190), ("course", "Course", 130),
            ("semester", "Semester", 85), ("present", "Present", 75), ("absent", "Absent", 75),
            ("late", "Late", 65), ("marked", "Total marked", 95), ("percent", "Present %", 90)]
        for col, title, width in headers:
            self.report_tree.heading(col, text=title)
            self.report_tree.column(col, width=width, anchor="center" if col in
                                    ("present", "absent", "late", "marked", "percent") else "w")
        self.report_tree.pack(fill="both", expand=True, pady=10)
        self.report_note = ttk.Label(self.report_tab, text="Present % = Present days ÷ (Present + Absent + Late) × 100")
        self.report_note.pack(anchor="w")

    @staticmethod
    def valid_date(value):
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def add_student(self):
        roll, name = self.roll_var.get().strip(), self.name_var.get().strip()
        if not roll or not name:
            messagebox.showwarning("Required fields", "Please enter both roll number and student name.")
            return
        try:
            self.db.add_student(roll, name, self.course_var.get(), self.sem_var.get())
            self.clear_student_form()
            self.refresh_all()
            messagebox.showinfo("Success", "Student added successfully.")
        except sqlite3.IntegrityError:
            messagebox.showerror("Duplicate roll number", "That roll number already exists.")

    def update_student(self):
        if not self.selected_student_id:
            messagebox.showwarning("Select student", "Select a student from the table first.")
            return
        roll, name = self.roll_var.get().strip(), self.name_var.get().strip()
        if not roll or not name:
            messagebox.showwarning("Required fields", "Roll number and name cannot be empty.")
            return
        try:
            self.db.update_student(self.selected_student_id, roll, name,
                                   self.course_var.get(), self.sem_var.get())
            self.refresh_all()
            messagebox.showinfo("Success", "Student details updated.")
        except sqlite3.IntegrityError:
            messagebox.showerror("Duplicate roll number", "That roll number already exists.")

    def delete_student(self):
        if not self.selected_student_id:
            messagebox.showwarning("Select student", "Select a student from the table first.")
            return
        if messagebox.askyesno("Confirm delete", "Delete this student and their attendance records?"):
            self.db.delete_student(self.selected_student_id)
            self.clear_student_form()
            self.refresh_all()

    def clear_student_form(self):
        self.selected_student_id = None
        for var in (self.roll_var, self.name_var, self.course_var, self.sem_var):
            var.set("")
        self.student_tree.selection_remove(self.student_tree.selection())

    def on_student_select(self, _event=None):
        selected = self.student_tree.selection()
        if not selected:
            return
        values = self.student_tree.item(selected[0], "values")
        self.selected_student_id = int(values[0])
        row = self.db.conn.execute("SELECT * FROM students WHERE id=?", (self.selected_student_id,)).fetchone()
        self.roll_var.set(row["roll_no"])
        self.name_var.set(row["name"])
        self.course_var.set(row["course"])
        self.sem_var.set(row["semester"])

    def refresh_students(self):
        for item in self.student_tree.get_children():
            self.student_tree.delete(item)
        for s in self.db.students(self.student_search.get()):
            self.student_tree.insert("", "end", values=(s["id"], s["roll_no"], s["name"], s["course"], s["semester"]))

    def refresh_attendance(self):
        day = self.att_date_var.get().strip()
        if not self.valid_date(day):
            messagebox.showerror("Invalid date", "Enter date in YYYY-MM-DD format, for example 2026-11-10.")
            return
        for item in self.att_tree.get_children():
            self.att_tree.delete(item)
        for row in self.db.attendance_for_day(day):
            self.att_tree.insert("", "end", values=(row["id"], row["roll_no"], row["name"], row["status"], row["remarks"]))

    def on_attendance_select(self, _event=None):
        selected = self.att_tree.selection()
        if not selected:
            return
        values = self.att_tree.item(selected[0], "values")
        if values[3] in ("Present", "Absent", "Late"):
            self.att_status_var.set(values[3])
        else:
            self.att_status_var.set("Present")
        self.att_remarks_var.set(values[4])

    def save_attendance(self):
        selected = self.att_tree.selection()
        if not selected:
            messagebox.showwarning("Select student", "Select a student row before saving attendance.")
            return
        day = self.att_date_var.get().strip()
        if not self.valid_date(day):
            messagebox.showerror("Invalid date", "Enter date in YYYY-MM-DD format.")
            return
        values = self.att_tree.item(selected[0], "values")
        self.db.save_attendance(int(values[0]), day, self.att_status_var.get(), self.att_remarks_var.get())
        self.refresh_attendance()
        self.refresh_dashboard()
        messagebox.showinfo("Saved", f"Attendance saved for {values[2]} on {day}.")

    def generate_report(self):
        start, end = self.start_var.get().strip(), self.end_var.get().strip()
        if not self.valid_date(start) or not self.valid_date(end):
            messagebox.showerror("Invalid date", "Use YYYY-MM-DD for both dates.")
            return
        if start > end:
            messagebox.showerror("Invalid range", "The start date must be on or before the end date.")
            return
        for item in self.report_tree.get_children():
            self.report_tree.delete(item)
        self.report_rows = self.db.report(start, end)
        for r in self.report_rows:
            marked = r["marked"] or 0
            pct = (r["present"] or 0) * 100 / marked if marked else 0
            self.report_tree.insert("", "end", values=(
                r["roll_no"], r["name"], r["course"], r["semester"],
                r["present"] or 0, r["absent"] or 0, r["late"] or 0, marked, f"{pct:.1f}%"))
        self.report_note.config(text=f"Report period: {start} to {end} | Percentage is based on recorded attendance only.")

    def export_report(self):
        if not hasattr(self, "report_rows"):
            self.generate_report()
            if not hasattr(self, "report_rows"):
                return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV files", "*.csv")],
            initialfile="attendance_report.csv")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Roll number", "Name", "Course", "Semester",
                             "Present", "Absent", "Late", "Total marked", "Present %"])
            for r in self.report_rows:
                marked = r["marked"] or 0
                pct = (r["present"] or 0) * 100 / marked if marked else 0
                writer.writerow([r["roll_no"], r["name"], r["course"], r["semester"],
                                 r["present"] or 0, r["absent"] or 0, r["late"] or 0,
                                 marked, f"{pct:.1f}%"])
        messagebox.showinfo("Export complete", f"CSV report saved to:\n{path}")

    def refresh_dashboard(self):
        total, present, absent, late = self.db.summary()
        for var, value in zip(self.stat_vars, (total, present, absent, late)):
            var.set(str(value))
        self.today_label.config(text=f"Date: {date.today().strftime('%d %B %Y')}")

    def refresh_all(self):
        self.refresh_students()
        self.refresh_attendance()
        self.refresh_dashboard()

    def on_close(self):
        self.db.close()
        self.destroy()


if __name__ == "__main__":
    app = AttendanceApp()
    app.mainloop()
