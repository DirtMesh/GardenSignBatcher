from __future__ import annotations

import queue
import threading
from pathlib import Path
from types import SimpleNamespace
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app.engine.config import load_config, save_config
from app.engine.input_reader import read_input_rows
from app.engine.logger import RunLogger
from app.engine.openscad import detect_openscad
from app.engine.planner import plan_jobs
from app.engine.resources import resource_path
from app.engine.runner import run_jobs


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Modular Garden Sign Batch Generator")
        self.geometry("900x800")

        self.msg_queue: queue.Queue[object] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.cancel_event = threading.Event()

        self.cfg = load_config()

        # OpenSCAD state
        self.openscad_path_var = tk.StringVar(value="")
        self.openscad_ok = False

        # Mapping: Treeview item id -> InputRow-like object (valid rows only)
        self.valid_item_to_row: dict[str, object] = {}

        # Selected rows for the current run (set by start_run, read by worker)
        self._selected_rows_for_run: list = []

        # Cell editor overlay
        self._cell_editor: ttk.Entry | None = None
        self._cell_editor_info: tuple[str, str] | None = None  # (iid, col_id)

        # Row numbering for GUI-generated rows (manual rows)
        self._next_row_num = 1

        self._build_ui()
        self._apply_config()
        self._ensure_trailing_blank_row()
        self._update_generate_state()

        # Schedule UI polling (dummy arg to satisfy some type checkers)
        self.after(100, self._drain_queue, None)

    # ---------------- UI ----------------

    def _build_ui(self) -> None:
        pad = {"padx": 6, "pady": 4}

        # ---- OpenSCAD Status ----
        frm_scad = ttk.LabelFrame(self, text="OpenSCAD")
        self._pack_x(frm_scad, pad)

        self.openscad_status_label = ttk.Label(frm_scad, text="Checking...")
        self.openscad_status_label.pack(side="left", padx=6, pady=4)

        ttk.Entry(frm_scad, textvariable=self.openscad_path_var).pack(
            side="left", fill="x", expand=True, padx=6, pady=4
        )

        ttk.Button(frm_scad, text="Auto-detect", command=self.autodetect_openscad).pack(
            side="left", padx=6, pady=4
        )
        ttk.Button(frm_scad, text="Browse...", command=self.browse_openscad).pack(
            side="left", padx=6, pady=4
        )

        # ---- Input ----
        frm_input = ttk.LabelFrame(self, text="Input (optional if entering rows manually)")
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
        ttk.Button(toolbar, text="Delete Selected", command=self.delete_selected_rows).pack(side="left", padx=6, pady=4)

        self.preview_status = ttk.Label(toolbar, text="")
        self.preview_status.pack(side="left", padx=12)

        # Treeview + scrollbars (in a container)
        tree_container = ttk.Frame(frm_prev)
        tree_container.pack(fill="both", expand=True, padx=6, pady=4)

        columns = ("row", "crop", "cultivar", "valid", "reason")
        self.tree = ttk.Treeview(
            tree_container,
            columns=columns,
            show="headings",
            selectmode="extended",
        )
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self._update_generate_state())
        self.tree.bind("<Double-1>", self._begin_cell_edit)
        self.tree.bind("<Delete>", lambda _e: self.delete_selected_rows())

        self.tree.heading("row", text="Row")
        self.tree.heading("crop", text="crop_name")
        self.tree.heading("cultivar", text="cultivar")
        self.tree.heading("valid", text="Valid")
        self.tree.heading("reason", text="Reason")

        self.tree.column("row", width=50, anchor="e")
        self.tree.column("crop", width=180, anchor="w")
        self.tree.column("cultivar", width=180, anchor="w")
        self.tree.column("valid", width=60, anchor="center")
        self.tree.column("reason", width=300, anchor="w")

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
        self.tree.tag_configure("blank", foreground="black")

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

        self.log_text = tk.Text(log_container, height=5, state="disabled", wrap="none")
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

    def pick_input(self) -> None:
        path = filedialog.askopenfilename(
            title="Select input file",
            filetypes=[("Excel or CSV", "*.xlsx *.xlsm *.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        self.input_var.set(path)
        self._update_sheets(Path(path))
        self.load_preview()

    def pick_output(self) -> None:
        path = filedialog.askdirectory(title="Select output folder")
        if path:
            self.out_var.set(path)
        self._update_generate_state()

    def _update_sheets(self, path: Path) -> None:
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

    def load_preview(self) -> None:
        # Commit any active edit so we do not lose changes right before append
        self._destroy_cell_editor(commit=True)

        # Append mode: do not clear existing rows.
        # Remove trailing blank row temporarily so it does not split appended rows.
        kids = self.tree.get_children()
        if kids and self._is_blank_row(kids[-1]):
            iid = kids[-1]
            self.tree.delete(iid)
            self.valid_item_to_row.pop(iid, None)

        try:
            input_s = self.input_var.get().strip()
            if not input_s:
                self.preview_status["text"] = "Select an input file (or enter rows manually)."
                return

            input_path = Path(input_s)
            if not input_path.exists():
                self.preview_status["text"] = "Input file not found."
                return

            sheet = self.sheet_var.get().strip() or None

            try:
                rows, issues, resolved_sheet = read_input_rows(input_path, sheet=sheet)
            except Exception as e:
                messagebox.showerror("Error", str(e))
                return

            issue_map: dict[int, str] = {}
            for iss in issues:
                issue_map.setdefault(int(iss.row_num), iss.reason)

            new_valid_iids: list[str] = []
            valid_count = 0
            max_seen_row_num = 0

            for r in rows:
                try:
                    rn = int(getattr(r, "row_num", 0) or 0)
                except Exception:
                    rn = 0
                if rn > max_seen_row_num:
                    max_seen_row_num = rn

                iid = self.tree.insert(
                    "",
                    "end",
                    values=(rn if rn else "", r.crop_name, r.cultivar, "", ""),
                    tags=("valid",),
                )
                self.valid_item_to_row[iid] = r
                self._recompute_generated_columns(iid)
                new_valid_iids.append(iid)
                valid_count += 1

            # Keep manual row numbers above any file row numbers we just added
            if max_seen_row_num > 0:
                self._next_row_num = max(self._next_row_num, max_seen_row_num + 1)

            invalid_count = 0
            for row_num, reason in sorted(issue_map.items()):
                self.tree.insert(
                    "",
                    "end",
                    values=(row_num, "", "", "No", reason),
                    tags=("invalid",),
                )
                invalid_count += 1

            # Select only the newly loaded valid rows
            self.tree.selection_remove(self.tree.selection())
            for iid in new_valid_iids:
                self.tree.selection_add(iid)

            if resolved_sheet:
                self.preview_status["text"] = f"Sheet: {resolved_sheet} | Added Valid: {valid_count} | Issues: {invalid_count}"
            else:
                self.preview_status["text"] = f"Added Valid: {valid_count} | Issues: {invalid_count}"

        finally:
            self._ensure_trailing_blank_row()
            self._update_generate_state()

    def select_valid_rows(self) -> None:
        self._destroy_cell_editor(commit=True)
        self.tree.selection_remove(self.tree.selection())
        for iid in self.valid_item_to_row.keys():
            self.tree.selection_add(iid)
        self._update_generate_state()

    def select_none(self) -> None:
        self._destroy_cell_editor(commit=True)
        self.tree.selection_remove(self.tree.selection())
        self._update_generate_state()

    # ---------------- Blank row management ----------------

    def _is_blank_row(self, iid: str) -> bool:
        vals = self.tree.item(iid, "values")
        if not vals:
            return True
        crop = str(vals[1]).strip() if len(vals) > 1 else ""
        cultivar = str(vals[2]).strip() if len(vals) > 2 else ""
        return (crop == "") and (cultivar == "")

    def _ensure_trailing_blank_row(self) -> None:
        kids = self.tree.get_children()
        if not kids:
            self._add_blank_row()
            return

        last = kids[-1]
        if not self._is_blank_row(last):
            self._add_blank_row()

    def _add_blank_row(self) -> str:
        iid = self.tree.insert(
            "",
            "end",
            values=("", "", "", "", ""),
            tags=("blank",),
        )
        return iid

    # ---------------- Cell editing ----------------

    def _begin_cell_edit(self, event: tk.Event) -> None:
        if self.worker and self.worker.is_alive():
            return

        iid = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)  # "#1", "#2", ...
        if not iid or not col:
            return

        columns = self.tree["columns"]  # ("row","crop","cultivar","valid","reason")
        col_index = int(col.replace("#", "")) - 1
        if col_index < 0 or col_index >= len(columns):
            return
        col_id = columns[col_index]

        # Only allow editing crop/cultivar
        if col_id not in {"crop", "cultivar"}:
            return

        bbox = self.tree.bbox(iid, col_id)
        if not bbox:
            return
        x, y, w, h = bbox

        # Commit any existing edit instead of discarding it
        self._destroy_cell_editor(commit=True)

        values = list(self.tree.item(iid, "values"))
        while len(values) < len(columns):
            values.append("")
        current = values[col_index]

        e = ttk.Entry(self.tree)
        e.insert(0, str(current))
        e.select_range(0, "end")
        e.focus_set()
        e.place(x=x, y=y, width=w, height=h)

        e.bind("<Return>", lambda _ev: self._destroy_cell_editor(commit=True))
        e.bind("<Escape>", lambda _ev: self._destroy_cell_editor(commit=False))
        e.bind("<FocusOut>", lambda _ev: self._destroy_cell_editor(commit=True))

        self._cell_editor = e
        self._cell_editor_info = (iid, col_id)

    def _destroy_cell_editor(self, commit: bool) -> None:
        if not self._cell_editor or not self._cell_editor_info:
            return

        e = self._cell_editor
        iid, col_id = self._cell_editor_info

        try:
            new_value = e.get().strip()
        finally:
            e.destroy()
            self._cell_editor = None
            self._cell_editor_info = None

        if not commit:
            return

        columns = self.tree["columns"]
        values = list(self.tree.item(iid, "values"))
        while len(values) < len(columns):
            values.append("")

        if col_id == "crop":
            values[columns.index("crop")] = new_value
        elif col_id == "cultivar":
            values[columns.index("cultivar")] = new_value

        self.tree.item(iid, values=values)

        self._recompute_generated_columns(iid)
        self._ensure_trailing_blank_row()
        self._update_generate_state()

    def _recompute_generated_columns(self, iid: str) -> None:
        columns = self.tree["columns"]
        values = list(self.tree.item(iid, "values"))
        while len(values) < len(columns):
            values.append("")

        crop = str(values[columns.index("crop")]).strip()
        cultivar = str(values[columns.index("cultivar")]).strip()

        # Blank row
        if (crop == "") and (cultivar == ""):
            values[columns.index("row")] = ""
            values[columns.index("valid")] = ""
            values[columns.index("reason")] = ""
            self.tree.item(iid, values=values, tags=("blank",))
            self.valid_item_to_row.pop(iid, None)
            return

        # Assign a row number if missing (manual rows)
        row_s = str(values[columns.index("row")]).strip()
        if row_s == "":
            values[columns.index("row")] = str(self._next_row_num)
            self._next_row_num += 1

        # Validity: both required
        if crop and cultivar:
            values[columns.index("valid")] = "Yes"
            values[columns.index("reason")] = ""
            self.tree.item(iid, values=values, tags=("valid",))

            # Ensure we have a backing object for manual rows
            if iid not in self.valid_item_to_row:
                try:
                    rn_int = int(values[columns.index("row")])
                except Exception:
                    rn_int = 0
                self.valid_item_to_row[iid] = SimpleNamespace(
                    row_num=rn_int,
                    crop_name=crop,
                    cultivar=cultivar,
                )
            else:
                r = self.valid_item_to_row[iid]
                if hasattr(r, "crop_name"):
                    r.crop_name = crop
                if hasattr(r, "cultivar"):
                    r.cultivar = cultivar
                # If the backing object has row_num, keep it aligned with the UI
                if hasattr(r, "row_num"):
                    try:
                        r.row_num = int(values[columns.index("row")])
                    except Exception:
                        pass
        else:
            values[columns.index("valid")] = "No"
            if not crop and not cultivar:
                reason = "Missing crop_name and cultivar"
            elif not crop:
                reason = "Missing crop_name"
            else:
                reason = "Missing cultivar"
            values[columns.index("reason")] = reason
            self.tree.item(iid, values=values, tags=("invalid",))
            self.valid_item_to_row.pop(iid, None)

    # ---------------- Delete ----------------

    def delete_selected_rows(self) -> None:
        if self.worker and self.worker.is_alive():
            return

        self._destroy_cell_editor(commit=True)

        selection = list(self.tree.selection())
        if not selection:
            return

        kids = self.tree.get_children()
        trailing_blank = kids[-1] if kids else None

        for iid in selection:
            if trailing_blank and iid == trailing_blank and self._is_blank_row(trailing_blank):
                continue
            self.tree.delete(iid)
            self.valid_item_to_row.pop(iid, None)

        self._ensure_trailing_blank_row()
        self._update_generate_state()

    # ---------------- OpenSCAD ----------------

    def autodetect_openscad(self) -> None:
        p = detect_openscad()
        self.openscad_path_var.set(str(p) if p else "")
        self._refresh_openscad_status()

    def browse_openscad(self) -> None:
        path = filedialog.askopenfilename(
            title="Select openscad.exe",
            filetypes=[("OpenSCAD executable", "openscad.exe"), ("All files", "*.*")],
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
        # Input file is optional if you are entering rows manually
        out_ok = bool(self.out_var.get().strip())
        selected_valid = any(iid in self.valid_item_to_row for iid in self.tree.selection())
        return self.openscad_ok and out_ok and selected_valid

    def _update_generate_state(self) -> None:
        if self.worker and self.worker.is_alive():
            self.run_btn["state"] = "disabled"
            return
        self.run_btn["state"] = "normal" if self._is_ready_to_generate() else "disabled"
        self._ensure_trailing_blank_row()

    # ---------------- Cancel ----------------

    def cancel_run(self) -> None:
        if self.worker and self.worker.is_alive():
            self.cancel_event.set()
            self.msg_queue.put("Cancel requested. Finishing current job...")
            self.cancel_btn["state"] = "disabled"

    # ---------------- Worker ----------------

    def start_run(self) -> None:
        if self.worker and self.worker.is_alive():
            return

        self._destroy_cell_editor(commit=True)

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

        out_s = self.out_var.get().strip()
        if not out_s:
            messagebox.showwarning("Output folder required", "Select an output folder.")
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

    def _run_worker(self) -> None:
        logger = None
        try:
            outdir = Path(self.out_var.get().strip())

            raw = self.openscad_path_var.get().strip()
            openscad = detect_openscad(Path(raw)) if raw else detect_openscad()
            if not openscad:
                self.msg_queue.put("ERROR: OpenSCAD not found.")
                return

            scad = resource_path("assets/ModularSignGenerator.scad")
            if not scad.exists():
                self.msg_queue.put(f"ERROR: SCAD file not found: {scad}")
                return

            logger = RunLogger(outdir)
            log = logger.tee(self.msg_queue.put)

            def on_progress(done: int, total: int, _job) -> None:
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

            # Input is optional now. Save last_input_dir only if present and exists.
            input_s = self.input_var.get().strip()
            if input_s:
                input_path = Path(input_s)
                if input_path.exists():
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

    def _append_log(self, msg: str) -> None:
        self.log_text["state"] = "normal"
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text["state"] = "disabled"

    def _clear_log(self) -> None:
        self.log_text["state"] = "normal"
        self.log_text.delete("1.0", "end")
        self.log_text["state"] = "disabled"

    def _apply_config(self) -> None:
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


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
