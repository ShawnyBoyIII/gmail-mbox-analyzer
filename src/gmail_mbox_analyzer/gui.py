import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from datetime import datetime

from .analyzer import analyze_mbox
from .cli import render_summary, render_search_summary
from .filter_exporter import generate_gmail_filters_xml


class AnalyzerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Gmail MBOX Analyzer")
        self.root.geometry("800x600")

        self.mbox_path = tk.StringVar()
        self.start_date = tk.StringVar()
        self.end_date = tk.StringVar()
        self.search_keyword = tk.StringVar()
        self.exclude_domains = tk.StringVar()
        self.top_n = tk.IntVar(value=20)
        self.bulk_only = tk.BooleanVar(value=False)
        self.filter_action = tk.StringVar(value="trash")

        self.last_analysis_result = None

        self.create_widgets()

    def create_widgets(self):
        # Top Frame for inputs
        input_frame = ttk.Frame(self.root, padding="10")
        input_frame.pack(fill=tk.X)

        # File Selection
        ttk.Label(input_frame, text="MBOX File:").grid(
            row=0, column=0, sticky=tk.W, pady=2
        )
        ttk.Entry(input_frame, textvariable=self.mbox_path, width=50).grid(
            row=0, column=1, sticky=tk.W, padx=5, pady=2
        )
        ttk.Button(input_frame, text="Browse...", command=self.browse_file).grid(
            row=0, column=2, pady=2
        )

        # Dates
        ttk.Label(input_frame, text="Start Date (YYYY-MM-DD):").grid(
            row=1, column=0, sticky=tk.W, pady=2
        )
        ttk.Entry(input_frame, textvariable=self.start_date, width=20).grid(
            row=1, column=1, sticky=tk.W, padx=5, pady=2
        )

        ttk.Label(input_frame, text="End Date (YYYY-MM-DD):").grid(
            row=2, column=0, sticky=tk.W, pady=2
        )
        ttk.Entry(input_frame, textvariable=self.end_date, width=20).grid(
            row=2, column=1, sticky=tk.W, padx=5, pady=2
        )

        # Search
        ttk.Label(input_frame, text="Search Keyword:").grid(
            row=3, column=0, sticky=tk.W, pady=2
        )
        ttk.Entry(input_frame, textvariable=self.search_keyword, width=30).grid(
            row=3, column=1, sticky=tk.W, padx=5, pady=2
        )

        # Exclude Domains
        ttk.Label(input_frame, text="Exclude Domains (comma separated):").grid(
            row=4, column=0, sticky=tk.W, pady=2
        )
        ttk.Entry(input_frame, textvariable=self.exclude_domains, width=50).grid(
            row=4, column=1, sticky=tk.W, padx=5, pady=2
        )

        # Options
        options_frame = ttk.Frame(input_frame)
        options_frame.grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=10)

        ttk.Label(options_frame, text="Top N:").pack(side=tk.LEFT)
        ttk.Entry(options_frame, textvariable=self.top_n, width=5).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Checkbutton(options_frame, text="Bulk Only", variable=self.bulk_only).pack(
            side=tk.LEFT, padx=10
        )

        self.run_button = ttk.Button(
            options_frame, text="Run Analysis", command=self.start_analysis
        )
        self.run_button.pack(side=tk.LEFT, padx=20)

        export_frame = ttk.Frame(input_frame)
        export_frame.grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=5)

        ttk.Label(export_frame, text="Filter Action:").pack(side=tk.LEFT)
        action_cb = ttk.Combobox(
            export_frame,
            textvariable=self.filter_action,
            values=["trash", "archive"],
            state="readonly",
            width=10,
        )
        action_cb.pack(side=tk.LEFT, padx=5)

        self.export_button = ttk.Button(
            export_frame,
            text="Export Filters XML",
            command=self.export_filters,
            state=tk.DISABLED,
        )
        self.export_button.pack(side=tk.LEFT, padx=10)

        # Bottom Frame for output
        output_frame = ttk.Frame(self.root, padding="10")
        output_frame.pack(fill=tk.BOTH, expand=True)

        self.text_area = tk.Text(output_frame, wrap=tk.WORD, font=("Consolas", 10))
        scrollbar = ttk.Scrollbar(
            output_frame, orient=tk.VERTICAL, command=self.text_area.yview
        )
        self.text_area.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def browse_file(self):
        path = filedialog.askopenfilename(
            title="Select MBOX File",
            filetypes=[("MBOX Files", "*.mbox"), ("All Files", "*.*")],
        )
        if path:
            self.mbox_path.set(path)

    def parse_date_str(self, date_str: str):
        date_str = date_str.strip()
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str)
        except ValueError:
            raise ValueError(f"Invalid date: '{date_str}'. Use YYYY-MM-DD.")

    def start_analysis(self):
        mbox_path = self.mbox_path.get().strip()
        if not mbox_path:
            messagebox.showerror("Error", "Please select an MBOX file.")
            return

        self.run_button.config(state=tk.DISABLED)
        self.text_area.delete(1.0, tk.END)
        self.text_area.insert(
            tk.END, "Analyzing... This may take a few minutes for large files.\n"
        )

        # Parse inputs
        try:
            start_date = self.parse_date_str(self.start_date.get())
            end_date = self.parse_date_str(self.end_date.get())
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            self.run_button.config(state=tk.NORMAL)
            return

        exclude_str = self.exclude_domains.get().strip()
        exclude_domains = (
            {d.strip() for d in exclude_str.split(",")} if exclude_str else set()
        )

        bulk_only = self.bulk_only.get()
        search_kw = self.search_keyword.get().strip()
        top_n = self.top_n.get()

        self.export_button.config(state=tk.DISABLED)
        self.last_analysis_result = None

        # Run in thread to not freeze GUI
        thread = threading.Thread(
            target=self.run_analysis_thread,
            args=(
                mbox_path,
                exclude_domains,
                bulk_only,
                start_date,
                end_date,
                search_kw,
                top_n,
            ),
        )
        thread.daemon = True
        thread.start()

    def run_analysis_thread(
        self,
        mbox_path,
        exclude_domains,
        bulk_only,
        start_date,
        end_date,
        search_kw,
        top_n,
    ):
        try:
            result = analyze_mbox(
                mbox_path,
                exclude_domains=exclude_domains,
                bulk_only=bulk_only,
                start_date=start_date,
                end_date=end_date,
            )

            if search_kw:
                output = render_search_summary(result, search_kw)
            else:
                output = render_summary(result, top_n)

            self.root.after(0, self.display_results, result, output)
        except Exception as e:
            self.root.after(0, self.display_error, str(e))

    def display_results(self, result, output: str):
        self.last_analysis_result = result
        self.text_area.delete(1.0, tk.END)
        self.text_area.insert(tk.END, output)
        self.run_button.config(state=tk.NORMAL)
        self.export_button.config(state=tk.NORMAL)

    def export_filters(self):
        if not self.last_analysis_result:
            return

        bulk_candidates = self.last_analysis_result.bulk_sender_counts[
            : min(self.top_n.get(), 50)
        ]
        emails = [r.sender_email for r in bulk_candidates if r.sender_email]

        if not emails:
            messagebox.showinfo(
                "Export Filters", "No likely bulk senders found to export."
            )
            return

        path = filedialog.asksaveasfilename(
            title="Save Filters XML",
            defaultextension=".xml",
            filetypes=[("XML Files", "*.xml"), ("All Files", "*.*")],
            initialfile="mailFilters.xml",
        )
        if not path:
            return

        try:
            xml_content = generate_gmail_filters_xml(emails, self.filter_action.get())
            with open(path, "w", encoding="utf-8") as f:
                f.write(xml_content)
            messagebox.showinfo(
                "Success", f"Exported Gmail XML filters for {len(emails)} bulk senders."
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save filters:\n{str(e)}")

    def display_error(self, error_msg: str):
        messagebox.showerror("Error", f"An error occurred:\n{error_msg}")
        self.run_button.config(state=tk.NORMAL)


def launch_gui():
    root = tk.Tk()
    AnalyzerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
