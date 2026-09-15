"""Shared presentation tokens and lightweight Tk components; no execution policy."""
import tkinter as tk
from tkinter import ttk

THEME_COLORS = {
    "app_bg": "#F4F7FB",
    "card_bg": "#FFFFFF",
    "soft_card_bg": "#F8FAFC",
    "primary": "#2563EB",
    "primary_hover": "#1D4ED8",
    "secondary": "#6B7280",
    "secondary_hover": "#4B5563",
    "border": "#E5E7EB",
    "text_primary": "#111827",
    "text_secondary": "#6B7280",
    "success": "#16A34A",
    "success_hover": "#15803D",
    "warning": "#F59E0B",
    "warning_hover": "#D97706",
    "danger": "#DC2626",
    "danger_hover": "#B91C1C",
    "info": "#0284C7",
    "info_hover": "#0369A1",
    "hero_bg": "#10233F",
    "hero_text": "#FFFFFF",
    "hero_muted": "#D7E2F2",
    "sidebar_bg": "#111827",
    "sidebar_hover": "#1F2937",
    "sidebar_text": "#F9FAFB",
    "table_alt": "#F9FAFB",
    "table_selected": "#DBEAFE",
    "badge_gray_bg": "#F3F4F6",
    "badge_blue_bg": "#E0F2FE",
    "badge_green_bg": "#DCFCE7",
    "badge_orange_bg": "#FEF3C7",
    "badge_red_bg": "#FEE2E2",
}
THEME_FONTS = {
    "main": ("Segoe UI", 11),
    "small": ("Segoe UI", 10),
    "section_title": ("Segoe UI Semibold", 12),
    "page_title": ("Segoe UI Semibold", 16),
    "table_header": ("Segoe UI Semibold", 10),
    "button": ("Segoe UI Semibold", 10),
}
THEME_SPACING = {
    "page_pad": (18, 0, 18, 18),
    "card_pad": (16, 0, 16, 16),
    "card_gap": 12,
    "button_pad": (14, 8),
}
BUTTON_STYLES = {
    "primary": {
        "style": "Primary.TButton",
        "bg": THEME_COLORS["primary"],
        "hover": THEME_COLORS["primary_hover"],
        "fg": "#FFFFFF",
    },
    "secondary": {
        "style": "Secondary.TButton",
        "bg": THEME_COLORS["secondary"],
        "hover": THEME_COLORS["secondary_hover"],
        "fg": "#FFFFFF",
    },
    "success": {
        "style": "Success.TButton",
        "bg": THEME_COLORS["success"],
        "hover": THEME_COLORS["success_hover"],
        "fg": "#FFFFFF",
    },
    "danger": {
        "style": "Danger.TButton",
        "bg": THEME_COLORS["danger"],
        "hover": THEME_COLORS["danger_hover"],
        "fg": "#FFFFFF",
    },
}

UI_SIZES = {"button_height": 38, "corner_radius": 10, "table_row": 28}
NAVIGATION = (
    ("heading", "HOME", ""), ("page", "Dashboard", "dashboard"),
    ("heading", "EXPERIMENT", ""), ("page", "Run Experiment", "summary"),
    ("page", "Compare Results", "figures"), ("page", "Propagation Path", "fault_path"),
    ("page", "Cross-Layer Safety", "cross_layer"),
    ("heading", "RESEARCH", ""), ("page", "Research Analysis", "research_analysis"),
    ("page", "RTL Security", "rtl_security"), ("heading", "REPORT", ""),
    ("page", "Exports", "exports"), ("page", "Final Validation", "final_validation"),
    ("heading", "ADVANCED", ""), ("page", "Experiment Builder", "custom"),
)
PAGE_LABELS = {key: label for kind, label, key in NAVIGATION if kind == "page"}
PAGE_LABELS["custom"] = "Advanced Experiment Builder"
RESEARCH_VIEWS = {"research_analysis": "Overview", "batch": "Aggregate Analysis",
                  "runtime_study": "Detector Study", "parameter_sweep": "Parameter Sweep"}
PAGE_LABELS.update({key: label for key, label in RESEARCH_VIEWS.items() if key != "research_analysis"})


def button_role(text, fallback="primary"):
    words = text.lower().strip()
    if words.startswith(("delete", "clear", "remove")):
        return "danger"
    if words.startswith(("run", "execute", "generate", "regenerate", "export", "quick sweep", "full sweep", "compare vs baseline", "compare all algorithms")):
        return "success"
    if words.startswith(("open guided", "open research", "start guided", "go to", "load", "reload", "inspect", "compare", "view")):
        return "primary"
    if words.startswith(("open", "cancel", "close", "browse", "save", "copy")):
        return "secondary"
    return fallback if fallback != "danger" else "secondary"


def action_button(parent, text, command):
    return ttk.Button(parent, text=text, command=command, style=BUTTON_STYLES[button_role(text)]["style"])


def configure_styles(root, presentation=False):
    style = ttk.Style(root)
    size = 12 if presentation else 11
    style.configure("TLabel", font=("Segoe UI", size), background=THEME_COLORS["card_bg"], foreground=THEME_COLORS["text_primary"])
    style.configure("TFrame", background=THEME_COLORS["card_bg"])
    style.configure("TLabelframe", background=THEME_COLORS["card_bg"])
    style.configure("TLabelframe.Label", font=THEME_FONTS["section_title"], background=THEME_COLORS["card_bg"], foreground=THEME_COLORS["hero_bg"])
    style.configure("Treeview", font=("Segoe UI", size), rowheight=32 if presentation else UI_SIZES["table_row"])
    style.configure("Treeview.Heading", font=THEME_FONTS["table_header"])
    style.configure("Help.TLabel", font=THEME_FONTS["small"], foreground=THEME_COLORS["text_secondary"])
    style.configure("Research.Toolbutton", font=THEME_FONTS["button"], padding=(12,8), background=THEME_COLORS["soft_card_bg"], foreground=THEME_COLORS["hero_bg"])
    style.map("Research.Toolbutton", background=[("selected",THEME_COLORS["primary"]),("active",THEME_COLORS["table_selected"])], foreground=[("selected","white")])
    style.configure("MetricTitle.TLabel", font=("Segoe UI Semibold", size), foreground=THEME_COLORS["hero_bg"])
    style.configure("MetricValue.TLabel", font=("Segoe UI Semibold", 23 if presentation else 21), foreground=THEME_COLORS["hero_bg"])
    style.configure("MetricDetail.TLabel", font=("Segoe UI", size), foreground=THEME_COLORS["text_secondary"])
    for values in BUTTON_STYLES.values():
        style.configure(values["style"], font=THEME_FONTS["button"], padding=THEME_SPACING["button_pad"], background=values["bg"], foreground=values["fg"])
        style.map(values["style"], background=[("disabled", THEME_COLORS["border"]), ("active", values["hover"])], foreground=[("disabled", THEME_COLORS["text_secondary"])])


HELP = {
    "FTTI": "Experimental timing budget used to evaluate containment within the configured interval; not a certification claim.",
    "Plant Manifestation": "Measured plant difference from the fault-free reference; this does not by itself mean hazard entry.",
    "Propagation Depth": "Deepest observed stage under the existing propagation rule. Exact timestamps appear in the table.",
    "Containment": "Whether the observed consequence returned to the defined safe region under the experimental containment rule.",
    "Safe State": "Applied protective mode. Entering this mode alone does not establish hazard containment.",
    "Silent Corruption": "Corruption classified as silent by the loaded experimental evidence; unavailable historical values remain N/A.",
    "Timing Monitor": "Disabled, observe-only detection, or the existing protective action. Independent of the selected runtime detector.",
    "Communication Safety Response": "Observe communication anomalies or enable the existing communication protective response.",
    "Replay Age": "Age of the historical sample replayed instead of the current communication update.",
    "Stuck Polarity": "Bit value held by the stuck-bit fault: 0 or 1.",
    "Intermittent": "ON and OFF intervals repeat within the configured fault duration, in simulator milliseconds.",
    "Seed": "Deterministic random seed passed unchanged to the simulator for repeatable experiments.",
    "Detection Latency": "Elapsed time from injection to observed detection; N/A when unavailable or not reached.",
    "Hazard": "Entry into the configured experimental hazardous region; plant manifestation alone is insufficient.",
    "Critical Exposure": "Accumulated time above the configured critical threshold, evaluated by the frozen hazard rule.",
}


class Tooltip:
    def __init__(self, widget, text):
        self.widget, self.text, self.window, self.timer = widget, text, None, None
        widget.bind("<Enter>", self.schedule, add="+")
        widget.bind("<FocusIn>", self.schedule, add="+")
        for event in ("<Leave>", "<FocusOut>", "<ButtonPress>", "<Destroy>"):
            widget.bind(event, self.hide, add="+")

    def schedule(self, event=None):
        self.hide()
        self.timer = self.widget.after(450, self.show)

    def show(self):
        self.timer = None
        if not self.widget.winfo_exists():
            return
        self.window = tk.Toplevel(self.widget)
        self.window.wm_overrideredirect(True)
        ttk.Label(self.window, text=self.text, wraplength=360, padding=12, relief="solid").pack()
        self.window.update_idletasks()
        x = min(self.widget.winfo_rootx(), self.widget.winfo_screenwidth()-self.window.winfo_reqwidth()-12)
        y = min(self.widget.winfo_rooty()+self.widget.winfo_height()+6, self.widget.winfo_screenheight()-self.window.winfo_reqheight()-12)
        self.window.geometry(f"+{max(0,x)}+{max(0,y)}")

    def hide(self, event=None):
        if self.timer:
            self.widget.after_cancel(self.timer)
            self.timer = None
        if self.window:
            self.window.destroy()
            self.window = None


def help_for(label):
    return next((text for key, text in HELP.items() if key.lower() in label.lower()), "")


def section(parent, title, row):
    frame = ttk.LabelFrame(parent, text=title, padding=12)
    frame.grid(row=row, column=0, sticky="ew", pady=(0, 12))
    frame.columnconfigure(0, weight=1)
    return frame


def status_category(message):
    lower = message.lower()
    if any(word in lower for word in ("failed", "error", "invalid")): return "Error"
    if "running" in lower or "regenerating" in lower: return "Running"
    if "passed" in lower or "completed" in lower or "exported" in lower: return "Completed"
    if "loaded" in lower and not lower.startswith("no "): return "Loaded"
    if "warning" in lower: return "Warning"
    if lower.startswith("no ") or "unavailable" in lower: return "No Results"
    return "Ready"


class StatusBanner(ttk.Frame):
    def __init__(self, parent, variable):
        super().__init__(parent, padding=(8, 6))
        self.variable = variable
        self.title = tk.StringVar(self)
        ttk.Label(self, textvariable=self.title, font=THEME_FONTS["section_title"]).pack(anchor="w")
        self.detail = ttk.Label(self, textvariable=variable, style="Help.TLabel", wraplength=760)
        self.detail.pack(fill="x")
        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.trace = variable.trace_add("write", self.refresh)
        self.bind("<Configure>", lambda e: self.detail.configure(wraplength=max(200,e.width-20)))
        self.bind("<Destroy>", self.cleanup, add="+")
        self.refresh()

    def refresh(self, *_):
        category = status_category(self.variable.get())
        self.title.set(category)
        if category == "Running":
            self.progress.pack(fill="x", pady=(5,0)); self.progress.start(20)
        else:
            self.progress.stop(); self.progress.pack_forget()

    def cleanup(self, event):
        if event.widget is self:
            self.variable.trace_remove("write", self.trace)


def responsive_labels(root):
    """Wrap help to the parent allocation without a label-size feedback loop."""
    for widget in root.winfo_children():
        if isinstance(widget, MetricCard):
            continue  # Metric cards own their responsive wrapping.
        is_ctk = type(widget).__name__ == 'CTkLabel'
        if isinstance(widget, (ttk.Label, tk.Label)) or is_ctk:
            try:
                titles = {"Advanced Custom Fault Builder": "Advanced Experiment Builder",
                          "Fault and Trojan-Parameter Sensitivity": "Parameter Sweep",
                          "Detector Summary": "Detailed Sweep Results"}
                if widget.cget("text") in titles:
                    widget.configure(text=titles[widget.cget("text")])
            except tk.TclError:
                pass
        if isinstance(widget, ttk.Label) or is_ctk:
            try:
                limit = int(widget.cget('wraplength') or 0)
                if limit:
                    def fit(event, w=widget, maximum=limit):
                        # The parent owns allocation; wrapping must not depend on
                        # the label's requested width, which itself changes on wrap.
                        if not w.winfo_exists():
                            return
                        width = max(120, event.width - 40)
                        target = min(maximum, width)
                        if abs(int(w.cget('wraplength') or 0) - target) > 8:
                            w.configure(wraplength=target)
                    widget.master.bind('<Configure>', fit, add='+')
            except (tk.TclError, ValueError):
                pass
        if isinstance(widget, ttk.Button):
            widget.configure(style=BUTTON_STYLES[button_role(str(widget.cget('text')))]['style'])
        if not is_ctk:
            responsive_labels(widget)


class MetricCard(ttk.Frame):
    """Presentation of a loaded value, with wrapping independent of its length."""
    def __init__(self, parent, title, variable, formatter=None, compact=False):
        super().__init__(parent, padding=14, relief='solid', borderwidth=1)
        self.columnconfigure(0, weight=1)
        self.value = tk.StringVar(self)
        self.detail = tk.StringVar(self)
        self.title_label = ttk.Label(self, text=title, font='', style='MetricTitle.TLabel', wraplength=240)
        self.value_label = ttk.Label(self, textvariable=self.value, font='', style='MetricTitle.TLabel' if compact else 'MetricValue.TLabel', wraplength=240)
        self.detail_label = ttk.Label(self, textvariable=self.detail, font='', style='MetricDetail.TLabel', wraplength=240)
        for row, label in enumerate((self.title_label, self.value_label, self.detail_label)):
            label.grid(row=row, column=0, sticky='ew', pady=(0, 6))
        def refresh(*_):
            value = variable.get() or 'N/A'
            main, detail = formatter(value) if formatter else (value, '')
            self.value.set(main); self.detail.set(detail)
        trace = variable.trace_add('write', refresh)
        self.bind('<Destroy>', lambda e: variable.trace_remove('write', trace) if e.widget is self else None)
        # Hidden notebook pages have no stable viewport allocation. Deferring
        # wrapping prevents their requested widths from feeding back into layout.
        last_width=[None]
        def wrap(event):
            if not self.winfo_ismapped() or event.width == last_width[0]:return
            last_width[0]=event.width
            for label in (self.title_label, self.value_label, self.detail_label):
                label.configure(wraplength=max(100, event.width - 48))
        self.bind('<Configure>', wrap)
        refresh()


class MetricGrid(ttk.Frame):
    """A small adaptive card grid using the application's existing palette."""
    def __init__(self, parent, max_columns=4, min_width=290):
        super().__init__(parent)
        self.cards = []; self.columns = 0
        self.max_columns, self.min_width = max_columns, min_width
        self.bind('<Configure>', lambda event: self.reflow(event.width) if self.winfo_ismapped() else None)

    def add(self, title, variable, **kwargs):
        card = MetricCard(self, title, variable, **kwargs)
        self.cards.append(card)
        self.columns = 0
        self.reflow(self.winfo_width())
        return card

    def reflow(self, width):
        columns = max(1, min(self.max_columns, width // self.min_width))
        if columns == self.columns:
            return
        for index in range(max(columns, self.columns)):
            self.columnconfigure(index, weight=1 if index < columns else 0,
                                 uniform='metrics' if index < columns else '')
        self.columns = columns
        for index, card in enumerate(self.cards):
            card.grid(row=index // columns, column=index % columns, sticky='nsew', padx=5, pady=5)
