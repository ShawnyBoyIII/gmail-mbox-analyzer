import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import time
import subprocess

class MemoryRecoveryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Memory Recovery Tool")
        self.root.geometry("600x400")

        self.source_path = tk.StringVar()
        self.dest_path = tk.StringVar()
        self.operation_mode = tk.StringVar(value="image")

        self.create_widgets()

    def create_widgets(self):
        # Frame for padding
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="Memory Card Data Recovery", font=("Helvetica", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # Source Selection
        ttk.Label(main_frame, text="Source Device/Image:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.source_path, width=40).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(main_frame, text="Browse", command=self.select_source).grid(row=1, column=2, pady=5)

        # Destination Selection
        ttk.Label(main_frame, text="Destination File/Folder:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.dest_path, width=40).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(main_frame, text="Browse", command=self.select_destination).grid(row=2, column=2, pady=5)

        # Options Frame
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="10")
        options_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=20)

        ttk.Radiobutton(options_frame, text="Image Drive (ddrescue)", variable=self.operation_mode, value="image").pack(anchor=tk.W)
        ttk.Radiobutton(options_frame, text="Recover Files (photorec)", variable=self.operation_mode, value="recover").pack(anchor=tk.W)

        # Progress Bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)

        # Status Label
        self.status_var = tk.StringVar(value="Ready to extract data.")
        ttk.Label(main_frame, textvariable=self.status_var).grid(row=5, column=0, columnspan=3, sticky=tk.W)

        # Action Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=3, pady=20)

        self.extract_btn = ttk.Button(button_frame, text="Extract Data", command=self.start_extraction)
        self.extract_btn.pack(side=tk.LEFT, padx=10)

        ttk.Button(button_frame, text="Exit", command=self.root.quit).pack(side=tk.LEFT, padx=10)

    def select_source(self):
        # We allow selecting any file (like an image file or a block device)
        path = filedialog.askopenfilename(title="Select Source Drive or Image")
        if path:
            self.source_path.set(path)

    def select_destination(self):
        # Depending on operation, we either want a file or a directory
        if self.operation_mode.get() == "image":
            path = filedialog.asksaveasfilename(title="Select Destination Image File", defaultextension=".img")
        else:
            path = filedialog.askdirectory(title="Select Destination Directory")

        if path:
            self.dest_path.set(path)

    def start_extraction(self):
        source = self.source_path.get()
        dest = self.dest_path.get()

        if not source or not dest:
            messagebox.showerror("Error", "Please select both source and destination.")
            return

        self.extract_btn.config(state=tk.DISABLED)
        self.status_var.set("Extraction started...")
        self.progress_var.set(0)

        # Run extraction in a separate thread so GUI doesn't freeze
        thread = threading.Thread(target=self.extract_data, args=(source, dest))
        thread.daemon = True
        thread.start()

    def extract_data(self, source, dest):
        mode = self.operation_mode.get()
        if mode == "image":
            self.run_ddrescue(source, dest)
        elif mode == "recover":
            self.run_photorec(source, dest)
        else:
            self.root.after(0, self.status_var.set, "Error: Unknown operation mode")
            self.root.after(0, lambda: self.extract_btn.config(state=tk.NORMAL))

    def run_ddrescue(self, source, dest):
        map_file = dest + ".map"

        # ddrescue args:
        # -d: direct disc access
        # -r3: retry bad sectors 3 times
        # source, dest, map_file
        cmd = ["ddrescue", "-d", "-r3", source, dest, map_file]

        try:
            # We use subprocess.Popen to be able to capture output or wait
            self.root.after(0, self.status_var.set, f"Running ddrescue...")

            # Start process
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

            # Read output (which ddrescue updates on the console)
            for line in process.stdout:
                # We could parse the line for progress, but for simplicity just update status
                # ddrescue uses carriage returns heavily, but Popen gives us lines
                pass

            process.wait()

            if process.returncode == 0:
                 self.root.after(0, self.status_var.set, "Imaging complete.")
                 self.root.after(0, lambda: messagebox.showinfo("Complete", "Data imaging complete."))
            else:
                 self.root.after(0, self.status_var.set, f"ddrescue finished with errors (code {process.returncode})")
                 self.root.after(0, lambda: messagebox.showwarning("Warning", f"Imaging finished but with errors. Partial image may have been created."))

        except FileNotFoundError:
            self.root.after(0, self.status_var.set, "Error: ddrescue not found")
            self.root.after(0, lambda: messagebox.showerror("Error", "ddrescue is not installed on the system."))
        except Exception as e:
            self.root.after(0, self.status_var.set, f"Error: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Error", f"An error occurred: {str(e)}"))
        finally:
            self.root.after(0, lambda: self.extract_btn.config(state=tk.NORMAL))
            self.root.after(0, self.progress_var.set, 100.0)

    def run_photorec(self, source, dest_dir):
        # photorec requires a directory for output
        if not os.path.isdir(dest_dir):
            try:
                os.makedirs(dest_dir)
            except OSError as e:
                self.root.after(0, self.status_var.set, f"Error creating directory: {str(e)}")
                self.root.after(0, lambda: messagebox.showerror("Error", f"Could not create destination directory: {str(e)}"))
                self.root.after(0, lambda: self.extract_btn.config(state=tk.NORMAL))
                return

        # photorec args:
        # /cmd allows passing commands to the prompt directly.
        # /d <dir> specifies the output directory
        # The syntax for photorec command line is somewhat complex, but for basic usage:
        cmd = ["photorec", "/d", dest_dir, "/cmd", source, "search"]

        try:
            self.root.after(0, self.status_var.set, f"Running photorec...")

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:
                pass

            process.wait()

            if process.returncode == 0:
                 self.root.after(0, self.status_var.set, "File recovery complete.")
                 self.root.after(0, lambda: messagebox.showinfo("Complete", f"File recovery complete. Check {dest_dir}."))
            else:
                 self.root.after(0, self.status_var.set, f"photorec finished with errors (code {process.returncode})")
                 self.root.after(0, lambda: messagebox.showwarning("Warning", f"Recovery finished but with errors. Some files may not be recovered."))

        except FileNotFoundError:
            self.root.after(0, self.status_var.set, "Error: photorec not found")
            self.root.after(0, lambda: messagebox.showerror("Error", "photorec (from the testdisk package) is not installed."))
        except Exception as e:
            self.root.after(0, self.status_var.set, f"Error: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Error", f"An error occurred: {str(e)}"))
        finally:
            self.root.after(0, lambda: self.extract_btn.config(state=tk.NORMAL))
            self.root.after(0, self.progress_var.set, 100.0)

def main():
    import sys
    # Just to handle a simple --help for verification purposes without starting the GUI
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("Memory Recovery GUI Tool")
        print("Usage: python3 memory_recovery_app.py")
        sys.exit(0)

    root = tk.Tk()
    app = MemoryRecoveryApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
