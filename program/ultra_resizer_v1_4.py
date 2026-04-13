"""
Multi-OS Ultra Resizer v1.4 — same behavior as the Windows script.
Requires: pillow, pandas. Tkinter is part of Python; on macOS use a build
that includes Tcl/Tk (e.g. python.org installer, or Homebrew python-tk).
"""
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import cast

from core.resizer import process_folder
from core.types import NoImagesError, OutputFormat, PadFillMode, ResizeConfig, ResizeMode

# --- Tk on macOS requires GUI updates on the main thread ---
def _on_main(root: tk.Tk, fn):
    root.after(0, fn)


def process_images_thread(root: tk.Tk):
    input_path = entry_input.get().strip()
    selected_format = format_var.get()
    if not input_path or not os.path.exists(input_path):
        messagebox.showerror("Error", "Please select a valid folder.")
        return
    try:
        width = int(entry_width.get())
        height = int(entry_height.get())
    except ValueError:
        messagebox.showerror("Error", "Please enter valid numeric width and height.")
        return

    include_subfolders = var_subfolders.get()
    resize_mode = cast(ResizeMode, resize_mode_var.get())
    pad_fill_mode = cast(PadFillMode, pad_fill_mode_var.get())
    threading.Thread(
        target=lambda: start_process(
            root,
            input_path,
            selected_format,
            width,
            height,
            include_subfolders,
            resize_mode,
            pad_fill_mode,
        ),
        daemon=True,
    ).start()


def start_process(
    root: tk.Tk,
    input_path: str,
    selected_format: str,
    width: int,
    height: int,
    include_subfolders: bool,
    resize_mode: ResizeMode,
    pad_fill_mode: PadFillMode,
):
    cfg = ResizeConfig(
        input_path=input_path,
        width=width,
        height=height,
        output_format=cast(OutputFormat, selected_format),
        include_subfolders=include_subfolders,
        resize_mode=resize_mode,
        pad_fill_mode=pad_fill_mode,
    )

    _on_main(root, lambda: btn_run.config(state="disabled"))

    def on_progress(p: int, t: int, _fn: str) -> None:
        _on_main(
            root,
            lambda p=p, t=t: label_status.config(
                text=f"Processing: {p} / {t} done...", fg="blue"
            ),
        )

    def on_status(s: str) -> None:
        if s == "COMPLETED!":
            return
        _on_main(root, lambda s=s: label_status.config(text=s, fg="blue"))

    try:
        result = process_folder(cfg, on_progress=on_progress, on_status=on_status)
    except NoImagesError as e:
        _on_main(root, lambda: messagebox.showinfo("No Images", str(e)))
        _on_main(root, lambda: btn_run.config(state="normal"))
        _on_main(root, lambda: label_status.config(text="Ready", fg="gray"))
        return
    except FileNotFoundError as e:
        _on_main(root, lambda: messagebox.showerror("Error", str(e)))
        _on_main(root, lambda: btn_run.config(state="normal"))
        _on_main(root, lambda: label_status.config(text="Ready", fg="gray"))
        return
    except Exception as e:
        _on_main(root, lambda: messagebox.showerror("Error", str(e)))
        _on_main(root, lambda: btn_run.config(state="normal"))
        _on_main(root, lambda: label_status.config(text="Ready", fg="gray"))
        return

    def _done():
        label_status.config(text="COMPLETED!", fg="green")
        btn_run.config(state="normal")
        msg = "Processing completed successfully."
        try:
            msg += f"\n\nComparison report:\n{result.comparison_html_path}"
        except Exception:
            pass
        messagebox.showinfo("Completed", msg)

    _on_main(root, _done)


# --- GUI ---
root = tk.Tk()
root.title("Multi-OS Ultra Resizer v1.4")
root.geometry("500x500")

main_frame = tk.Frame(root, padx=25, pady=20)
main_frame.pack(expand=True, fill="both")


def browse():
    path = filedialog.askdirectory()
    if path:
        entry_input.delete(0, tk.END)
        entry_input.insert(0, path)


tk.Label(main_frame, text="ULTRA RESIZER v1.4", font=("Arial", 16, "bold"), fg="#16a085").pack(
    pady=10
)
tk.Label(main_frame, text="Select Folder:").pack(anchor="w")
entry_input = tk.Entry(main_frame, width=45)
entry_input.pack(pady=5)
tk.Button(main_frame, text="Browse", command=browse).pack()

var_subfolders = tk.BooleanVar(value=True)
tk.Checkbutton(
    main_frame,
    text="Include subfolders (mirror structure in output)",
    variable=var_subfolders,
).pack(anchor="w", pady=(10, 0))

tk.Label(main_frame, text="Format:").pack(anchor="w", pady=(15, 0))
format_var = tk.StringVar(value="JPG")
ttk.Combobox(
    main_frame, textvariable=format_var, values=["JPG", "PNG", "WebP"], state="readonly"
).pack()

tk.Label(main_frame, text="Resolution (W x H):").pack(anchor="w", pady=(15, 0))
dim_frame = tk.Frame(main_frame)
dim_frame.pack()
entry_width = tk.Entry(dim_frame, width=10)
entry_width.insert(0, "850")
entry_width.grid(row=0, column=0, padx=5)
entry_height = tk.Entry(dim_frame, width=10)
entry_height.insert(0, "1280")
entry_height.grid(row=0, column=1, padx=5)

tk.Label(main_frame, text="Sizing:").pack(anchor="w", pady=(12, 0))
resize_mode_var = tk.StringVar(value="fit")
ttk.Combobox(
    main_frame,
    textvariable=resize_mode_var,
    values=["fit", "exact_pad", "exact_stretch"],
    state="readonly",
    width=42,
).pack(anchor="w")

tk.Label(main_frame, text="Bars color (letterbox only):").pack(anchor="w", pady=(8, 0))
pad_fill_mode_var = tk.StringVar(value="white")
ttk.Combobox(
    main_frame,
    textvariable=pad_fill_mode_var,
    values=["white", "black", "extend", "blur", "auto"],
    state="readonly",
    width=42,
).pack(anchor="w")

label_status = tk.Label(main_frame, text="Ready", font=("Arial", 10, "italic"), fg="gray")
label_status.pack(pady=20)

btn_run = tk.Button(
    main_frame,
    text="START PROCESSING",
    bg="#2c3e50",
    fg="white",
    font=("Arial", 12, "bold"),
    pady=10,
    command=lambda: process_images_thread(root),
)
btn_run.pack(fill="x")

root.mainloop()
