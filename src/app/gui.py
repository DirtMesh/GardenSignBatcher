from __future__ import annotations

import threading
import queue
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from app.engine.input_reader import read_input_rows
from app.engine.openscad import detect_openscad
from app.engine.planner import plan_jobs
from app.engine.resources import resource_path
from app.engine.runner import run_jobs
from app.engine.logger import RunLogger
from app.engine.config import load_config, save_config


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("OpenSCAD Sign Batch Generator")
        self.geometry("900x850")

        self.msg_queue: queue.Queue[object] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.cancel_event = threading.Event()

        self.cfg = load_config()

        # OpenSCAD state
        self.openscad_path_var = tk.StringVar(value="")
        self.openscad_ok = False

        # Mapping: Treeview item id -> InputRow (valid rows only)
        self.valid_item_to_row: dict[str, object] = {}

        # Selected rows for the current run (set by start_run, read by worker)
        self._selected_rows_for_run: list = []

        self._build_ui()
        self._apply_config()
        self._update_generate_state()

        # Schedule UI polling (dummy arg to satisfy some type checkers)
        self.after(100, self._drain_queue, None)

    # ---------------- UI ----------------

    def _build_ui(self):
        pad = {"padx": 6, "pady": 4}

        # ---- OpenSCAD Status ----
        frm_scad = ttk.LabelFrame(self, text="OpenSCAD")
        self._pack_x(frm_scad, pad)

        self.openscad_status_label = ttk.Label(frm_scad, text="Checking...")
        self.openscad_status_label.pack(side="left", padx=6, pady=4)

        ttk.Entry(frm_scad, textvariable=self.openscad_path_var).pack(
            side="left", fill="x", expand=True, padx=6, pady=4
        )

        ttk.Button(frm_scad, text="Auto-detect", command=self.autodetect_openscad).pack(side="left", padx=6, pady=4)
        ttk.Button(frm_scad, text="Browse...", command=self.browse_openscad).pack(side="left", padx=6, pady=4)


        # ---- Input ----
        frm_input = ttk.LabelFrame(self, text="Input")
        self._pack_x(frm_input, pad)

        self.input_var = tk.StringVar()
        ttk.Entry(frm_input, textvariable=self.input_var).pack(side="left", fill="x", expand=True, **pad)
        ttk.Button(frm_input, text="Browse...", command=self.pick_input).pack(side="left", **pad)

        # ---- Sheet ----
        frm_sheet = ttk.Frame(self)
        frm_sheet.pack(fill="x", **pad)

        ttk.Label(frm_sheet, text="Sheet:").pack(side="left", **pad)
        self.sheet_var = tk.StringVar()
        self.sheet_combo = ttk.Combobox(frm_sheet, textvariable=self.sheet_var, state="disabled", width=40)
        self.sheet_combo.pack(side="left", **pad)
        self.sheet_combo.bind("<<ComboboxSelected>>", lambda _e: self.load_preview())

        ttk.Button(frm_sheet, text="Reload Preview", command=self.load_preview).pack(side="left", **pad)

        # ---- Output ----
        frm_out = ttk.LabelFrame(self, text="Output")
        frm_out.pack(fill="x", **pad)

        self.out_var = tk.StringVar()
        ttk.Entry(frm_out, textvariable=self.out_var).pack(side="left", fill="x", expand=True, **pad)
        ttk.Button(frm_out, text="Browse...", command=self.pick_output).pack(side="left", **pad)

        # Update Generate enabled state when input/output changes
        self.input_var.trace_add("write", self._on_var_change)
        self.out_var.trace_add("write", self._on_var_change)

        # ---- Options ----
        frm_opts = ttk.LabelFrame(self, text="Options")
        frm_opts.pack(fill="x", **pad)

        self.export_a = tk.BooleanVar(value=True)
        self.export_b = tk.BooleanVar(value=True)
        self.overwrite = tk.BooleanVar(value=False)
        self.stop_on_error = tk.BooleanVar(value=False)
        self.start_index = tk.IntVar(value=1)

        ttk.Checkbutton(frm_opts, text="Export A", variable=self.export_a).pack(side="left", **pad)
        ttk.Checkbutton(frm_opts, text="Export B", variable=self.export_b).pack(side="left", **pad)
        ttk.Checkbutton(frm_opts, text="Overwrite", variable=self.overwrite).pack(side="left", **pad)
        ttk.Checkbutton(frm_opts, text="Stop on error", variable=self.stop_on_error).pack(side="left", **pad)

        ttk.Label(frm_opts, text="Start index:").pack(side="left", **pad)
        ttk.Entry(frm_opts, textvariable=self.start_index, width=6).pack(side="left", **pad)

        # ---- Paned area (Preview + Log) ----
        panes = ttk.Panedwindow(self, orient="vertical")
        panes.pack(fill="both", expand=True, padx=6, pady=4)


        frm_prev = ttk.LabelFrame(panes, text="Preview (select rows to generate)")
        frm_log = ttk.LabelFrame(panes, text="Log")

        panes.add(frm_prev, weight=3)
        panes.add(frm_log, weight=2)

        # ---- Preview toolbar (selection + status) ----
        toolbar = ttk.Frame(frm_prev)
        toolbar.pack(fill="x", padx=6, pady=4)

        ttk.Button(toolbar, text="Select Valid", command=self.select_valid_rows).pack(side="left", padx=6, pady=4)
        ttk.Button(toolbar, text="Select None", command=self.select_none).pack(side="left", padx=6, pady=4)

        self.preview_status = ttk.Label(toolbar, text="")
        self.preview_status.pack(side="left", padx=12)

        # Treeview + scrollbars (in a container)
        tree_container = ttk.Frame(frm_prev)
        tree_container.pack(fill="both", expand=True, padx=6, pady=4)

        columns = ("row", "crop", "cultivar", "valid", "reason")
        self.tree = ttk.Treeview(
            tree_container,  # IMPORTANT: parent is tree_container, not frm_prev
            columns=columns,
            show="headings",
            selectmode="extended",
        )
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self._update_generate_state())

        self.tree.heading("row", text="Row")
        self.tree.heading("crop", text="crop_name")
        self.tree.heading("cultivar", text="cultivar")
        self.tree.heading("valid", text="Valid")
        self.tree.heading("reason", text="Reason")

        self.tree.column("row", width=30, anchor="e")
        self.tree.column("crop", width=120, anchor="w")
        self.tree.column("cultivar", width=120, anchor="w")
        self.tree.column("valid", width=30, anchor="center")
        self.tree.column("reason", width=200, anchor="w")

        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        # Tag styling
        self.tree.tag_configure("invalid", foreground="gray")
        self.tree.tag_configure("valid", foreground="black")

        # ---- Controls (kept outside panes) ----
        frm_ctrl = ttk.Frame(self)
        frm_ctrl.pack(fill="x", **pad)

        self.run_btn = ttk.Button(frm_ctrl, text="Generate", command=self.start_run)
        self.run_btn.pack(side="left", **pad)

        self.cancel_btn = ttk.Button(frm_ctrl, text="Cancel", command=self.cancel_run, state="disabled")
        self.cancel_btn.pack(side="left", **pad)

        self.progress = ttk.Progressbar(frm_ctrl, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True, **pad)

        # ---- Log ----
        log_toolbar = ttk.Frame(frm_log)
        log_toolbar.pack(fill="x", padx=6, pady=4)

        ttk.Button(log_toolbar, text="Copy log", command=self.copy_log_to_clipboard).pack(side="left")

        log_container = ttk.Frame(frm_log)
        log_container.pack(fill="both", expand=True)

        self.log_text = tk.Text(log_container, height=12, state="disabled", wrap="none")
        self.log_text.pack(side="left", fill="both", expand=True)

        log_scroll = ttk.Scrollbar(log_container, orient="vertical", command=self.log_text.yview)
        log_scroll.pack(side="right", fill="y")

        self.log_text.configure(yscrollcommand=log_scroll.set)

    @staticmethod
    def _pack_x(widget: tk.Widget, pad: dict) -> None:
        widget.pack(fill="x", **pad)

    # ---------------- Actions ----------------

    def _on_var_change(self, _name: str, _index: str, _op: str) -> None:
        self._update_generate_state()

    def pick_input(self):
        path = filedialog.askopenfilename(
            title="Select input file",
            filetypes=[("Excel or CSV", "*.xlsx *.xlsm *.csv"), ("All files", "*.*")]
        )
        if not path:
            return
        self.input_var.set(path)
        self._update_sheets(Path(path))
        self.load_preview()
        self._update_generate_state()

    def pick_output(self):
        path = filedialog.askdirectory(title="Select output folder")
        if path:
            self.out_var.set(path)
        self._update_generate_state()

    def _update_sheets(self, path: Path):
        if path.suffix.lower() == ".csv":
            self.sheet_combo["values"] = []
            self.sheet_combo.set("")
            self.sheet_combo["state"] = "disabled"
            return

        try:
            from app.engine.excel import list_sheets
            sheets = list_sheets(path)
            self.sheet_combo["values"] = sheets
            self.sheet_combo.set(sheets[0] if sheets else "")
            self.sheet_combo["state"] = "readonly" if sheets else "disabled"
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def copy_log_to_clipboard(self) -> None:
        try:
            text = self.log_text.get("1.0", "end-1c")
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()
            messagebox.showinfo("Copied", "Log copied to clipboard.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ---------------- Preview loading ----------------

    def load_preview(self):
        self._clear_preview()
        input_s = self.input_var.get().strip()
        if not input_s:
            self.preview_status["text"] = "Select an input file."
            self._update_generate_state()
            return

        input_path = Path(input_s)
        if not input_path.exists():
            self.preview_status["text"] = "Input file not found."
            self._update_generate_state()
            return

        sheet = self.sheet_var.get().strip() or None

        try:
            rows, issues, resolved_sheet = read_input_rows(input_path, sheet=sheet)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self._update_generate_state()
            return

        issue_map: dict[int, str] = {}
        for iss in issues:
            issue_map.setdefault(int(iss.row_num), iss.reason)

        valid_count = 0
        for r in rows:
            iid = self.tree.insert(
                "",
                "end",
                values=(r.row_num, r.crop_name, r.cultivar, "Yes", ""),
                tags=("valid",),
            )
            self.valid_item_to_row[iid] = r
            valid_count += 1

        invalid_count = 0
        for row_num, reason in sorted(issue_map.items()):
            self.tree.insert(
                "",
                "end",
                values=(row_num, "", "", "No", reason),
                tags=("invalid",),
            )
            invalid_count += 1

        self.select_valid_rows()

        if resolved_sheet:
            self.preview_status["text"] = f"Sheet: {resolved_sheet} | Valid: {valid_count} | Issues: {invalid_count}"
        else:
            self.preview_status["text"] = f"Valid: {valid_count} | Issues: {invalid_count}"

        self._update_generate_state()

    def _clear_preview(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.valid_item_to_row.clear()

    def select_valid_rows(self):
        self.tree.selection_remove(self.tree.selection())
        for iid in self.valid_item_to_row.keys():
            self.tree.selection_add(iid)
        self._update_generate_state()

    def select_none(self):
        self.tree.selection_remove(self.tree.selection())
        self._update_generate_state()

    # ---------------- OpenSCAD ----------------

    def autodetect_openscad(self) -> None:
        p = detect_openscad()
        self.openscad_path_var.set(str(p) if p else "")
        self._refresh_openscad_status()

    def browse_openscad(self) -> None:
        path = filedialog.askopenfilename(
            title="Select openscad.exe",
            filetypes=[("OpenSCAD executable", "openscad.exe"), ("All files", "*.*")]
        )
        if not path:
            return
        self.openscad_path_var.set(path)
        self._refresh_openscad_status()

    def _refresh_openscad_status(self) -> None:
        raw = self.openscad_path_var.get().strip()
        p = Path(raw) if raw else None

        resolved = detect_openscad(p) if p else detect_openscad()
        self.openscad_ok = resolved is not None

        if self.openscad_ok:
            self.openscad_status_label["text"] = f"Found: {resolved}"
            if str(resolved) != raw:
                self.openscad_path_var.set(str(resolved))
        else:
            self.openscad_status_label["text"] = "Not found. Install OpenSCAD or browse to openscad.exe."

        self._update_generate_state()

    # ---------------- Generate enable/disable ----------------

    def _is_ready_to_generate(self) -> bool:
        input_ok = bool(self.input_var.get().strip())
        out_ok = bool(self.out_var.get().strip())
        selected_valid = any(iid in self.valid_item_to_row for iid in self.tree.selection())
        return self.openscad_ok and input_ok and out_ok and selected_valid

    def _update_generate_state(self) -> None:
        if self.worker and self.worker.is_alive():
            self.run_btn["state"] = "disabled"
            return
        self.run_btn["state"] = "normal" if self._is_ready_to_generate() else "disabled"

    # ---------------- Cancel ----------------

    def cancel_run(self):
        if self.worker and self.worker.is_alive():
            self.cancel_event.set()
            self.msg_queue.put("Cancel requested. Finishing current job...")
            self.cancel_btn["state"] = "disabled"

    # ---------------- Worker ----------------

    def start_run(self):
        if self.worker and self.worker.is_alive():
            return

        selected_rows = []
        for iid in self.tree.selection():
            r = self.valid_item_to_row.get(iid)
            if r is not None:
                selected_rows.append(r)

        if not selected_rows:
            messagebox.showwarning("No rows selected", "Select at least one valid row to generate.")
            return

        if not self.openscad_ok:
            messagebox.showwarning("OpenSCAD not found", "Install OpenSCAD or browse to openscad.exe.")
            return

        self.cancel_event.clear()
        self.progress["value"] = 0
        self.progress["maximum"] = 100

        self.run_btn["state"] = "disabled"
        self.cancel_btn["state"] = "normal"
        self._clear_log()

        self._selected_rows_for_run = selected_rows

        self.worker = threading.Thread(target=self._run_worker, daemon=True)
        self.worker.start()

    def _run_worker(self):
        logger = None
        try:
            input_path = Path(self.input_var.get().strip())
            outdir = Path(self.out_var.get().strip())

            raw = self.openscad_path_var.get().strip()
            openscad = detect_openscad(Path(raw)) if raw else detect_openscad()
            if not openscad:
                self.msg_queue.put("ERROR: OpenSCAD not found.")
                return

            scad = resource_path("assets/sign_generator.scad")
            if not scad.exists():
                self.msg_queue.put(f"ERROR: SCAD file not found: {scad}")
                return

            logger = RunLogger(outdir)
            log = logger.tee(self.msg_queue.put)

            def on_progress(done: int, total: int, _job):
                self.msg_queue.put(("PROGRESS", done, total))

            rows = list(self._selected_rows_for_run)
            log(f"Starting generation. Selected valid rows: {len(rows)}")

            jobs = plan_jobs(
                rows,
                outdir,
                export_a=self.export_a.get(),
                export_b=self.export_b.get(),
                start_index=self.start_index.get(),
                overwrite=self.overwrite.get(),
            )

            results = run_jobs(
                jobs,
                openscad_exe=openscad,
                scad_file=scad,
                stop_on_error=self.stop_on_error.get(),
                on_log=log,
                should_cancel=self.cancel_event.is_set,
                on_progress=on_progress,
            )

            if self.cancel_event.is_set():
                log("Run cancelled by user.")

            ok = sum(1 for r in results if r.ok)
            fail = sum(1 for r in results if not r.ok)

            log(f"Done. OK={ok} FAIL={fail}")
            log(f"Log file: {logger.path}")

            cfg = self.cfg
            cfg["last_input_dir"] = str(input_path.parent)
            cfg["last_output_dir"] = str(outdir)
            cfg["export_a"] = self.export_a.get()
            cfg["export_b"] = self.export_b.get()
            cfg["overwrite"] = self.overwrite.get()
            cfg["stop_on_error"] = self.stop_on_error.get()
            cfg["start_index"] = self.start_index.get()
            cfg["openscad_path"] = self.openscad_path_var.get().strip()
            save_config(cfg)

        except Exception as e:
            self.msg_queue.put(f"ERROR: {e}")
        finally:
            if logger is not None:
                logger.close()
            self.msg_queue.put("__DONE__")

    # ---------------- UI Helpers ----------------

    def _drain_queue(self, *_args: object) -> None:
        try:
            while True:
                item = self.msg_queue.get_nowait()

                if item == "__DONE__":
                    self.progress["value"] = 100
                    self.cancel_btn["state"] = "disabled"
                    self._update_generate_state()

                elif isinstance(item, tuple) and item[0] == "PROGRESS":
                    _, done, total = item
                    percent = int((done / total) * 100) if total else 0
                    self.progress["value"] = percent

                else:
                    self._append_log(str(item))

        except queue.Empty:
            pass

        self.after(100, self._drain_queue, None)

    def _append_log(self, msg: str):
        self.log_text["state"] = "normal"
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text["state"] = "disabled"

    def _clear_log(self):
        self.log_text["state"] = "normal"
        self.log_text.delete("1.0", "end")
        self.log_text["state"] = "disabled"

    def _apply_config(self):
        if self.cfg.get("last_output_dir"):
            self.out_var.set(self.cfg["last_output_dir"])
        if self.cfg.get("openscad_path"):
            self.openscad_path_var.set(self.cfg["openscad_path"])

        self.export_a.set(self.cfg.get("export_a", True))
        self.export_b.set(self.cfg.get("export_b", True))
        self.overwrite.set(self.cfg.get("overwrite", False))
        self.stop_on_error.set(self.cfg.get("stop_on_error", False))
        self.start_index.set(self.cfg.get("start_index", 1))

        self._refresh_openscad_status()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
