import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import sys
from matcher import reconcile
from excel_handler import read_students, write_report, write_template
from bank_parser import parse_bank_statement


def resource_path(filename):
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base_path / filename


def default_output_path():
    if getattr(sys, "frozen", False):
        return Path.home() / "Documents" / "Payment_Reconciliation_Report.xlsx"
    return Path("output") / "Payment_Reconciliation_Report.xlsx"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Payment Reconciliation System")
        icon_path = resource_path("PaymentReconciliation.ico")
        if icon_path.exists():
            self.iconbitmap(str(icon_path))
        self.geometry("850x560")
        self.minsize(760, 500)

        self.student_file = tk.StringVar()
        self.bank_file = tk.StringVar()
        self.output_file = tk.StringVar(value=str(default_output_path()))

        self.build_ui()

    def build_ui(self):
        pad = {"padx": 18, "pady": 10}
        title = ttk.Label(self, text="PAYMENT RECONCILIATION SYSTEM",
                          font=("Segoe UI", 20, "bold"))
        title.pack(pady=(20, 4))

        ttk.Label(self, text="Compare your student payment list with a bank/PhonePe statement",
                  font=("Segoe UI", 10)).pack(pady=(0, 15))

        frame = ttk.Frame(self)
        frame.pack(fill="x", **pad)

        self.file_row(frame, 0, "Student Excel / CSV", self.student_file, self.choose_student)
        self.file_row(frame, 1, "Bank Statement PDF", self.bank_file, self.choose_bank)
        self.file_row(frame, 2, "Output Excel", self.output_file, self.choose_output)

        ttk.Separator(self).pack(fill="x", padx=18, pady=10)

        self.run_btn = ttk.Button(self, text="START RECONCILIATION", command=self.run)
        self.run_btn.pack(pady=12, ipadx=20, ipady=8)

        ttk.Button(
            self,
            text="GENERATE STUDENT TEMPLATE",
            command=self.generate_template,
        ).pack(pady=(0, 8), ipadx=12, ipady=5)

        self.status = tk.StringVar(value="Ready.")
        ttk.Label(self, textvariable=self.status, font=("Segoe UI", 10)).pack(pady=5)

        self.tree = ttk.Treeview(self, columns=("metric", "value"), show="headings", height=8)
        self.tree.heading("metric", text="Metric")
        self.tree.heading("value", text="Value")
        self.tree.column("metric", width=320)
        self.tree.column("value", width=180)
        self.tree.pack(fill="both", expand=True, padx=18, pady=12)

    def file_row(self, parent, row, label, variable, command):
        ttk.Label(parent, text=label, width=22).grid(row=row, column=0, sticky="w")
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", padx=8)
        ttk.Button(parent, text="Browse", command=command).grid(row=row, column=2)
        parent.columnconfigure(1, weight=1)

    def choose_student(self):
        f = filedialog.askopenfilename(
            title="Select student list",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if f:
            self.student_file.set(f)

    def choose_bank(self):
        f = filedialog.askopenfilename(
            title="Select bank statement PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if f:
            self.bank_file.set(f)

    def choose_output(self):
        f = filedialog.asksaveasfilename(
            title="Save reconciliation report",
            initialdir=str(Path.home() / "Documents"),
            initialfile="Payment_Reconciliation_Report.xlsx",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")]
        )
        if f:
            self.output_file.set(f)
        return bool(f)

    def generate_template(self):
        initial_directory = (
            Path.home() / "Documents"
            if getattr(sys, "frozen", False)
            else Path(__file__).resolve().parent
        )
        selected_path = filedialog.asksaveasfilename(
            title="Save student template",
            initialdir=str(initial_directory),
            initialfile="Student_Template.xlsx",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
        )
        if not selected_path:
            return

        output = Path(selected_path)
        #if output.exists() and not messagebox.askyesno(
        #    "Replace template?",
        #    f"The template already exists. Replace it?\n\n{output}",
        #):
        #    return

        try:
            write_template(output)
            self.status.set(f"Template created: {output}")
            messagebox.showinfo("Template created", f"Student template saved to:\n\n{output}")
        except Exception as e:
            self.status.set("Error creating template.")
            messagebox.showerror("Error", str(e))

    def run(self):
        if not self.student_file.get() or not self.bank_file.get():
            messagebox.showwarning("Missing files", "Please select both the student Excel/CSV and bank statement PDF.")
            return

        if not self.choose_output():
            self.status.set("Ready. Report save cancelled.")
            return

        try:
            self.run_btn.config(state="disabled")
            self.status.set("Reading student list...")
            self.update_idletasks()

            students = read_students(self.student_file.get())

            self.status.set("Reading bank statement...")
            self.update_idletasks()
            bank_transactions = parse_bank_statement(self.bank_file.get())

            self.status.set("Matching transactions...")
            self.update_idletasks()
            result = reconcile(students, bank_transactions)

            self.status.set("Creating Excel report...")
            self.update_idletasks()
            output = write_report(result, self.output_file.get())

            for item in self.tree.get_children():
                self.tree.delete(item)

            for k, v in result["summary"].items():
                self.tree.insert("", "end", values=(k, v))

            self.status.set(f"Completed. Report saved to: {output}")
            messagebox.showinfo("Completed", f"Reconciliation completed.\n\nReport:\n{output}")

        except Exception as e:
            self.status.set("Error.")
            messagebox.showerror("Error", str(e))
        finally:
            self.run_btn.config(state="normal")

if __name__ == "__main__":
    App().mainloop()
