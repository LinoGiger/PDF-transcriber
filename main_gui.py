import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import sys
import os
from main import process_pdf

class PDFTranscriberGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("PDF Transcriber")
        self.input_path = ""
        self.output_path = ""

        self.input_label = tk.Label(root, text="Input PDF:")
        self.input_label.grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.input_entry = tk.Entry(root, width=40)
        self.input_entry.grid(row=0, column=1, padx=5, pady=5)
        self.input_browse = tk.Button(root, text="Browse", command=self.browse_input)
        self.input_browse.grid(row=0, column=2, padx=5, pady=5)

        self.output_label = tk.Label(root, text="Output TXT:")
        self.output_label.grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.output_entry = tk.Entry(root, width=40)
        self.output_entry.grid(row=1, column=1, padx=5, pady=5)
        self.output_browse = tk.Button(root, text="Browse", command=self.browse_output)
        self.output_browse.grid(row=1, column=2, padx=5, pady=5)

        # Add page selection
        self.pages_label = tk.Label(root, text="Pages (e.g. 1,2,5-7):")
        self.pages_label.grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.pages_entry = tk.Entry(root, width=40)
        self.pages_entry.grid(row=2, column=1, padx=5, pady=5)

        self.go_button = tk.Button(root, text="Go", command=self.run_process)
        self.go_button.grid(row=3, column=1, pady=10)

        self.status_text = tk.Text(root, height=8, width=60, state="disabled")
        self.status_text.grid(row=4, column=0, columnspan=3, padx=5, pady=5)

    def browse_input(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if path:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, path)

    def browse_output(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if path:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, path)

    def run_process(self) -> None:
        input_path = self.input_entry.get().strip()
        output_path = self.output_entry.get().strip()
        page_selection = self.pages_entry.get().strip()
        if not input_path or not output_path:
            messagebox.showerror("Error", "Please select both input and output files.")
            return
        # Validate page selection
        page_numbers = None
        if page_selection:
            try:
                import fitz
                doc = fitz.open(input_path)
                total_pages = len(doc)
                doc.close()
                from main import parse_page_selection
                page_numbers = parse_page_selection(page_selection, total_pages)
                if not page_numbers:
                    raise ValueError("No valid pages selected.")
            except Exception as e:
                messagebox.showerror("Error", f"Invalid page selection: {e}")
                return
        self.append_status(f"Processing: {input_path} -> {output_path}\n")
        self.go_button.config(state="disabled")
        threading.Thread(target=self._process_pdf_thread, args=(input_path, output_path, page_numbers), daemon=True).start()

    def _process_pdf_thread(self, input_path: str, output_path: str, page_numbers: list[int] | None) -> None:
        try:
            process_pdf(input_path, output_path, page_numbers=page_numbers)
            self.append_status("Done!\n")
            messagebox.showinfo("Success", f"Processing complete. Output saved to {output_path}")
        except Exception as e:
            self.append_status(f"Error: {e}\n")
            messagebox.showerror("Error", str(e))
        finally:
            self.go_button.config(state="normal")

    def append_status(self, message: str) -> None:
        self.status_text.config(state="normal")
        self.status_text.insert(tk.END, message)
        self.status_text.see(tk.END)
        self.status_text.config(state="disabled")

def main() -> None:
    root = tk.Tk()
    app = PDFTranscriberGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 
