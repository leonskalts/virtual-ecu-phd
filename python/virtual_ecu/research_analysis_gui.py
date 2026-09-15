"""One research workspace; original frames/indices retain their loading callbacks."""
import tkinter as tk
from tkinter import ttk
from .gui_design import RESEARCH_VIEWS, action_button, section, responsive_labels, MetricGrid


class ResearchAnalysisWorkspace:
    def __init__(self, app):
        self.app = app
        self.selected = 'research_analysis'
        self.selection = tk.StringVar(app, value=self.selected)
        self.selectors = {}
        self.overview_vars = []
        self.headers = {}
        for key in RESEARCH_VIEWS:
            parent = app.page_frames[key].content
            # Replace the visual hero only; no original content is reparented.
            for child in parent.grid_slaves(row=0):
                child.grid_remove()
            for child in parent.grid_slaves():
                info=child.grid_info()
                if int(info['row'])>=1:child.grid_configure(row=int(info['row'])+1)
            app._build_tab_header(parent,row=0,title='Research Analysis',description='Explore aggregate campaigns, compare detector/intervention behavior, or study sensitivity across fault parameters.')
            header = section(parent, 'Analysis view', 1)
            self.headers[key] = header
            bar = ttk.Frame(header); bar.grid(row=0, column=0, sticky='ew')
            self.selectors[key] = []
            for index, (view, label) in enumerate(RESEARCH_VIEWS.items()):
                button = ttk.Radiobutton(bar, text=label, variable=self.selection, value=view,
                                        command=lambda view=view: self.show(view), style='Research.Toolbutton')
                button.grid(row=0, column=index, sticky='ew', padx=3)
                bar.columnconfigure(index, weight=1)
                self.selectors[key].append(button)
        parent = app.page_frames['research_analysis'].content
        intro = section(parent, 'Choose a research utility', 2)
        ttk.Label(intro, text='These optional research tools are independent of the normal single-experiment workflow. For a first experiment, use Dashboard → Start Guided Experiment. For final paper evidence, use Final Validation.', wraplength=760).grid(sticky='ew')
        definitions = (
            ('batch', 'Inspect many completed fault-injection runs together.', 'Aggregate CSV campaigns · fault-type averages · detection trends · thermal and safe-state outcomes'),
            ('runtime_study', 'Compare runtime detectors and safety actions on the same scenarios.', 'Detection latency · missed detections · observe-only vs intervention · detector/action trade-offs'),
            ('parameter_sweep', 'Measure how detector behavior changes with fault severity, duration, and activation timing.', 'Robustness · sensitivity · detector coverage · latency · clean alarms'),
        )
        grid=MetricGrid(parent,max_columns=3,min_width=290)
        grid.grid(row=3,column=0,sticky='ew',pady=8)
        for key, purpose, useful in definitions:
            variable=tk.StringVar(app,value=purpose+'\n'+useful)
            self.overview_vars.append(variable)
            card=grid.add(RESEARCH_VIEWS[key],variable,compact=True,
                          formatter=lambda value:tuple(value.split('\n',1)))
            action_button(card, 'Open '+RESEARCH_VIEWS[key], lambda key=key: self.show(key)).grid(row=3, column=0, sticky='w',pady=(8,0))
        # Historical file names and the required Batch Findings/Comparison labels stay intact.
        ttk.Label(self.headers['batch'], text='Aggregate Analysis is a general campaign/result viewer. It summarizes many completed runs but does not define the final frozen v5/v6 validation evidence.', style='Help.TLabel', wraplength=760).grid(row=2,column=0,sticky='ew',pady=(10,0))
        for key in RESEARCH_VIEWS:
            responsive_labels(app.page_frames[key].content)

    def show(self, key):
        if key in RESEARCH_VIEWS:
            self.selected = key
            self.app._navigate_to_page(key)

    def record(self, key):
        if key in RESEARCH_VIEWS:
            self.selected = key
            self.selection.set(key)
            return 'research_analysis'
        return key
