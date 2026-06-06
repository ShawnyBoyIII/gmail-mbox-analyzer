import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from datetime import datetime, timezone, timedelta

from .analyzer import analyze_mbox
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
        self.inactive_only = tk.BooleanVar(value=False)

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

        ttk.Checkbutton(
            options_frame, text="Inactive Senders (>1 yr)", variable=self.inactive_only
        ).pack(side=tk.LEFT, padx=10)

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

        self.generate_search_button = ttk.Button(
            export_frame,
            text="Generate Search for Selected",
            command=self.generate_search_for_selected,
            state=tk.DISABLED,
        )
        self.generate_search_button.pack(side=tk.LEFT, padx=10)

        # Summary Frame (Health Score)
        self.summary_frame = ttk.Frame(self.root, padding="10")
        self.summary_frame.pack(fill=tk.X)
        self.summary_label = ttk.Label(
            self.summary_frame,
            text="Ready to analyze your inbox.",
            font=("Helvetica", 11),
        )
        self.summary_label.pack(side=tk.LEFT)

        # Bottom Frame for output
        output_frame = ttk.Frame(self.root, padding="10")
        output_frame.pack(fill=tk.BOTH, expand=True)

        # Create Treeview
        columns = ("name", "email", "count", "bulk", "date", "category")
        self.tree = ttk.Treeview(
            output_frame, columns=columns, show="headings", selectmode="extended"
        )

        # Define headings
        self.tree.heading("name", text="Sender Name")
        self.tree.heading("email", text="Email Address")
        self.tree.heading("count", text="Message Count")
        self.tree.heading("bulk", text="Likely Bulk")
        self.tree.heading("date", text="Last Email")
        self.tree.heading("category", text="Category")

        # Define columns
        self.tree.column("name", width=150, anchor=tk.W)
        self.tree.column("email", width=200, anchor=tk.W)
        self.tree.column("count", width=100, anchor=tk.E)
        self.tree.column("bulk", width=100, anchor=tk.E)
        self.tree.column("date", width=100, anchor=tk.W)
        self.tree.column("category", width=100, anchor=tk.W)

        # Scrollbar for Treeview
        scrollbar = ttk.Scrollbar(
            output_frame, orient=tk.VERTICAL, command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)

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
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Update summary text
        self.summary_label.config(
            text="Analyzing... This may take a few minutes for large files."
        )

        # Parse inputs
        try:
            start_date = self.parse_date_str(self.start_date.get())
            end_date = self.parse_date_str(self.end_date.get())
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            self.summary_label.config(text="Analysis failed.")
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

            self.root.after(0, self.display_results, result, top_n, search_kw)
        except Exception as e:
            self.root.after(0, self.display_error, str(e))

    def display_results(self, result, top_n: int, search_kw: str):
        self.last_analysis_result = result

        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Calculate Health Score Summary
        total_bulk = sum(r.bulk_count for r in result.sender_counts)
        bulk_percent = (
            (total_bulk / result.total_messages * 100)
            if result.total_messages > 0
            else 0
        )
        mb_used = result.total_attachment_bytes / (1024 * 1024)

        health_score = 100
        health_score -= min(50, int(bulk_percent))  # Up to 50 point deduction for bulk
        health_score -= min(
            30, int(mb_used / 100)
        )  # Up to 30 point deduction for heavy attachments (>3GB)

        top_category = "None"
        if result.category_counts:
            # Filter out Uncategorized for the top stat if there are other categories
            known_cats = {
                k: v for k, v in result.category_counts.items() if k != "Uncategorized"
            }
            if known_cats:
                top_category = max(known_cats, key=known_cats.get)

        summary_text = (
            f"Health Score: {health_score}/100 | "
            f"Total Messages: {result.total_messages:,} | "
            f"Likely Bulk: {bulk_percent:.1f}% | "
            f"Attachments: {mb_used:.1f} MB | "
            f"Top Category: {top_category}"
        )
        self.summary_label.config(text=summary_text)

        # Filter and sort data
        records_to_display = result.sender_counts

        if self.inactive_only.get():
            one_year_ago = datetime.now(timezone.utc) - timedelta(days=365)
            filtered_records = []
            for r in records_to_display:
                if r.last_email_date is None:
                    filtered_records.append(r)
                else:
                    date_to_compare = r.last_email_date
                    if date_to_compare.tzinfo is None:
                        date_to_compare = date_to_compare.replace(tzinfo=timezone.utc)
                    if date_to_compare < one_year_ago:
                        filtered_records.append(r)
            records_to_display = filtered_records

        if search_kw:
            keyword = search_kw.lower()
            records_to_display = [
                r
                for r in records_to_display
                if keyword in r.sender_email.lower() or keyword in r.sender_name.lower()
            ]

        records_to_display = records_to_display[:top_n]

        # Populate treeview
        for record in records_to_display:
            name = record.sender_name or ""
            date_str = (
                record.last_email_date.strftime("%Y-%m-%d")
                if record.last_email_date
                else "Unknown"
            )
            self.tree.insert(
                "",
                tk.END,
                values=(
                    name,
                    record.sender_email,
                    record.count,
                    record.bulk_count,
                    date_str,
                    record.category,
                ),
            )

        self.run_button.config(state=tk.NORMAL)
        self.export_button.config(state=tk.NORMAL)
        self.generate_search_button.config(state=tk.NORMAL)

    def generate_search_for_selected(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo(
                "Selection Required",
                "Please select one or more senders from the list to generate a search string.",
            )
            return

        search_parts = []
        for item in selected_items:
            # The values are (name, email, count, bulk)
            # We want the email
            email = self.tree.item(item, "values")[1]
            if email:
                search_parts.append(f"from:{email}")

        if not search_parts:
            return

        search_string = " OR ".join(search_parts)

        # Show in a popup
        popup = tk.Toplevel(self.root)
        popup.title("Gmail Search Query")
        popup.geometry("600x250")

        ttk.Label(
            popup,
            text="Copy and paste the following string into Gmail's search bar:",
            padding=10,
        ).pack(fill=tk.X)

        search_text = tk.Text(popup, wrap=tk.WORD, height=5, font=("Consolas", 10))
        search_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        search_text.insert(tk.END, search_string)
        search_text.config(state=tk.DISABLED)  # Make it read-only

        # Select all text automatically for easy copying
        search_text.tag_add("sel", "1.0", tk.END)
        search_text.focus_set()

        def copy_to_clipboard():
            self.root.clipboard_clear()
            self.root.clipboard_append(search_string)
            self.root.update()
            copy_btn.config(text="Copied! ✓")

            def reset_btn():
                if copy_btn.winfo_exists():
                    copy_btn.config(text="Copy to Clipboard")

            popup.after(2000, reset_btn)

        copy_btn = ttk.Button(
            popup, text="Copy to Clipboard", command=copy_to_clipboard
        )
        copy_btn.pack(pady=(5, 10))

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
