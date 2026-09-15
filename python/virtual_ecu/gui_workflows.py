"""Small summary cards added to existing pages, without changing evidence loaders."""
import csv
import math
import tkinter as tk
from tkinter import ttk
from .gui_design import PAGE_LABELS, THEME_FONTS, action_button, StatusBanner, section, MetricGrid


def insert_card(parent, title, row=1):
    for child in parent.grid_slaves():
        info=child.grid_info()
        if int(info['row']) >= row:child.grid_configure(row=int(info['row'])+1)
    return section(parent,title,row)


def summary_label(parent, variable, row=0):
    label=ttk.Label(parent,textvariable=variable,wraplength=760,justify='left')
    label.grid(row=row,column=0,sticky='ew',pady=4)
    parent.bind('<Configure>',lambda e:label.configure(wraplength=max(240,e.width-28)),add='+')
    return label


def watch(variables, callback):
    # The owner is the application; these traces share its lifetime.
    for variable in variables:variable.trace_add('write',lambda *_:callback())
    callback()


def extrema(rows, key, label, maximum=False):
    available=[]
    for row in rows:
        try:value=float(row.get(key,''))
        except (TypeError,ValueError):continue
        if math.isfinite(value) and value>=0:available.append((value,row))
    if not available:return 'N/A'
    best=(max if maximum else min)(v for v,_ in available)
    names=sorted({str(r.get(label,'N/A')) for v,r in available if v==best})
    return f'{best:g} · '+', '.join(names)+(' (tie)' if len(names)>1 else '')


def polish_workflows(app):
    for key,label in PAGE_LABELS.items():
        app.page_labels[key]=label
        app.notebook.tab(app.page_frames[key],text=label)
    parent=lambda key:app.page_frames[key].content
    app.workflow_summary_vars={}
    def textcard(key,title):
        card=insert_card(parent(key),title)
        var=tk.StringVar(app);app.workflow_summary_vars[key]=var
        summary_label(card,var)
        return card,var

    card=insert_card(parent('figures'),'Loaded comparison')
    var=tk.StringVar(app);app.workflow_summary_vars['figures']=var
    grid=MetricGrid(card,max_columns=3,min_width=280);grid.grid(row=0,column=0,sticky='ew')
    app.comparison_card_vars={name:tk.StringVar(app,value='N/A') for name in ('Left Case','Right Case','Key Difference')}
    app.comparison_cards={name:grid.add(name,value,compact=True) for name,value in app.comparison_card_vars.items()}
    expanded=tk.BooleanVar(app,value=False)
    toggle=ttk.Checkbutton(card,text='Detailed Comparison Summary',variable=expanded)
    toggle.grid(row=1,column=0,sticky='w',pady=8)
    details=ttk.Frame(card);details.columnconfigure(0,weight=1)
    summary_label(details,var)
    def expand():
        details.grid(row=2,column=0,sticky='ew') if expanded.get() else details.grid_remove()
    toggle.configure(command=expand)
    app.comparison_details=details;app.comparison_details_toggle=toggle
    empty=ttk.Label(card,text='No comparison selected. Run a predefined story or load saved left and right results.',wraplength=760)
    def comparison(grid=grid,var=var):
        results=app.current_plot_results
        if results is None:
            var.set('No comparison selected. Run a predefined story or load saved left and right results.')
            grid.grid_remove();toggle.grid_remove();details.grid_remove()
            empty.grid(row=0,column=0,sticky='ew')
            for value in app.comparison_card_vars.values():value.set('N/A')
            return
        empty.grid_remove();grid.grid();toggle.grid();expand()
        lines=[];cross_layer=False
        for side,title in (('left','Left Case'),('right','Right Case')):
            result=results.get(side)
            name=app.summary_vars[side]['Campaign Name'].get() if result else 'N/A'
            label,is_cross_layer=comparison_run_label(result,name)
            cross_layer |= is_cross_layer
            lines.append(side.title()+': '+label)
            app.comparison_card_vars[title].set(label.split(' · maximum coolant:')[0])
        verdict=app.comparison_verdict_var.get()
        app.comparison_card_vars['Key Difference'].set(comparison_key_difference(verdict,results if cross_layer else None))
        if cross_layer:
            lines.append('Plots retain stored campaign labels. For instrumented cross-layer stages and detection, use Cross-Layer Safety; the legacy campaign propagation table does not classify these fault options.')
        lines.append(verdict)
        var.set('\n'.join(lines))
    watch([app.comparison_verdict_var,*[app.summary_vars[side]['Campaign Name'] for side in ('left','right')]],comparison)
    app.refresh_comparison_cards=comparison
    action_button(card,'Load comparison / Run Experiment',lambda:app._navigate_to_page('summary')).grid(row=3,column=0,sticky='w',pady=4)

    card,var=textcard('custom','Advanced workflow')
    var.set('For staged, multi-fault, or custom scenarios. For a single guided Cross-Layer experiment, use Cross-Layer Safety.')
    action_button(card,'Open Guided Cross-Layer Experiment',app.open_guided_experiment).grid(row=1,column=0,sticky='w',pady=4)

    card,var=textcard('fault_path','Read the propagation path')
    var.set('FAULT ORIGIN identifies the injected subsystem. MAIN OUTCOME identifies the observed manifestation. Sensing → Timing / Link → Control / Memory → Actuation → Plant. Load a comparison to inspect its evidence.')
    action_button(card,'Load comparison',lambda:app._navigate_to_page('summary')).grid(row=1,column=0,sticky='w')

    card,var=textcard('batch','Campaign at a glance')
    def batch():
        rows=app.batch_rows
        text='No campaign loaded. Load Aggregate CSV to inspect runs and per-fault findings.'
        if rows:
            states={r.get('final_safe_state','') for r in rows}
            order=('normal','precautionary_cooling','limp_home','controlled_shutdown')
            known=[s for s in order if s in states]
            text=(f'Runs: {len(rows)} · Fault classes: {app.batch_fault_classes_var.get()}\n'
                  f'Fault models: {app.batch_fault_types_var.get()}\n'
                  'Fastest detection (ms): '+extrema(rows,'detection_latency_ms','fault_type')+'\n'
                  'Highest thermal severity (°C): '+extrema(rows,'max_coolant_temperature_c','fault_type',True)+'\n'
                  'Most severe final safe state: '+(known[-1] if known else 'N/A'))
        app.workflow_summary_vars['batch'].set(text)
    watch([app.batch_status_text,app.batch_findings_var],batch)
    action_button(card,'Load Aggregate CSV',app.load_batch_results).grid(row=1,column=0,sticky='w')

    card=insert_card(parent('runtime_study'),'Detector and action comparison')
    app.workflow_summary_vars['runtime_study']=tk.StringVar(app)
    detection=tk.StringVar(app);intervention=tk.StringVar(app)
    summary_label(section(card,'Detection performance',0),detection)
    summary_label(section(card,'Intervention outcome',1),intervention)
    ttk.Label(card,text='Detection speed and thermal outcome answer different questions; inspect the detector/action table below.',wraplength=760,style='Help.TLabel').grid(row=2,column=0,sticky='ew')
    def detector():
        values=app.runtime_study_summary_vars
        detection.set('Fastest detector: '+values['Fastest Detector'].get()+' · Missed detections: '+values['Missed Detections'].get())
        intervention.set('Lowest mean maximum coolant: '+values['Lowest Mean Max Coolant'].get())
        app.workflow_summary_vars['runtime_study'].set('DETECTION PERFORMANCE · '+detection.get()+'\nINTERVENTION OUTCOME · '+intervention.get())
    watch(list(app.runtime_study_summary_vars.values()),detector)

    card=insert_card(parent('parameter_sweep'),'Sweep results at a glance')
    app.workflow_summary_vars['parameter_sweep']=tk.StringVar(app)
    grid=MetricGrid(card,max_columns=5,min_width=290);grid.grid(row=0,column=0,sticky='ew')
    app.sweep_card_vars={name:tk.StringVar(app,value='N/A') for name in ('Best Coverage','Best Median Latency','Hybrid Coverage','Hybrid Median Latency','Clean Alarms')}
    app.sweep_cards={name:grid.add(name,value,formatter=split_metric_detail) for name,value in app.sweep_card_vars.items()}
    ttk.Label(card,text='Ties are preserved; no artificial ranking is applied.',style='Help.TLabel',wraplength=760).grid(row=1,column=0,sticky='ew',pady=8)
    def sweep():
        rows=app.parameter_sweep_rows
        values=sweep_metric_values(rows,app.parameter_sweep_summary_vars)
        for name,value in values.items():app.sweep_card_vars[name].set(value)
        app.workflow_summary_vars['parameter_sweep'].set('\n'.join(name+': '+value.replace('\n',' · ') for name,value in values.items()))
    watch([app.parameter_sweep_status_text,*app.parameter_sweep_summary_vars.values()],sweep)

    card,var=textcard('rtl_security','Selected target story')
    def rtl():
        values=app.rtl_run_summary_vars['trojan']
        parts=[name+': '+values[name].get() for name in ('RTL Target','Detector','Payload Time','First Detection','Latency','Final Safe State','Max Coolant')]
        # Trigger and payload prose come directly from the accepted study taxonomy.
        target=values['RTL Target'].get()
        if target in ('', '-', 'N/A'):target=app.rtl_plot_target_choice.get()
        taxonomy=[]
        path=app.project_root/'results/rtl_hardware_trojan_study_v1/attack_taxonomy_table.csv' if hasattr(app,'project_root') else None
        if path and path.is_file():
            with path.open(newline='') as handle:taxonomy=list(csv.DictReader(handle))
        match=next((r for r in taxonomy if r.get('rtl_target_id','').startswith(target.split(' ')[0].lower()+'_') or r.get('rtl_target_id')==target or r.get('rtl_target_id')==values['RTL Target'].get() or r.get('rtl_target_id','').removeprefix('ht1_').removeprefix('ht2_').removeprefix('ht3_').removeprefix('ht4_')==target),None)
        if match:parts.extend(('Trigger: '+match.get('trigger','N/A'),'Payload: '+match.get('payload','N/A')))
        app.workflow_summary_vars['rtl_security'].set(' · '.join(parts)+'\nP = Payload · DET = Selected detector alarm · DTC = ECU diagnostic event')
    # ROOT is a read-only path; no new study data are synthesized.
    from .cross_layer_safety import PROJECT_ROOT
    app.project_root=PROJECT_ROOT
    watch([*app.rtl_run_summary_vars['trojan'].values(),app.rtl_plot_target_choice],rtl)

    card,var=textcard('exports','Last export')
    var.set('No export generated in this session. Load a comparison to enable the export actions.')
    def exported():
        message=app.status_text.get()
        if message.startswith('Exported '):app.workflow_summary_vars['exports'].set('Completed · '+message)
    watch([app.status_text],exported)
    # A compact, consistent state banner for long-running research workflows.
    for key,variable in (('summary',app.status_text),('batch',app.batch_status_text),('runtime_study',app.runtime_study_status_text),('parameter_sweep',app.parameter_sweep_status_text),('rtl_security',app.rtl_plot_status_text)):
        frame=parent(key)
        row=max((int(child.grid_info()['row']) for child in frame.grid_slaves()),default=0)+1
        StatusBanner(frame,variable).grid(row=row,column=0,sticky='ew',pady=8)
    polish_responsive_layout(app)


def adaptive_pair(container, left, right, *, row=0, breakpoint=1450):
    """Keep two wide scientific views side-by-side only when both fit."""
    last=[None]
    def reflow(event):
        stacked=event.width<breakpoint
        if stacked==last[0]:return
        last[0]=stacked
        container.columnconfigure(0,weight=1)
        container.columnconfigure(1,weight=0 if stacked else 1)
        left.grid_configure(row=row,column=0,columnspan=2 if stacked else 1,padx=0,pady=(0,10))
        right.grid_configure(row=row+1 if stacked else row,column=0 if stacked else 1,columnspan=2 if stacked else 1,padx=0,pady=(0,10))
    container.bind('<Configure>',reflow,add='+')


def polish_responsive_layout(app):
    from .gui_design import responsive_labels
    # Existing fixed-width explanatory text competed with controls in these rows.
    controls=app.detection_algorithm_selector.master
    for child in controls.grid_slaves():
        info=child.grid_info()
        if isinstance(child,ttk.Label) and int(info['column'])==2:
            child.grid_configure(row=2+int(info['row']),column=0,columnspan=4,sticky='ew',pady=5)
    controls.columnconfigure(0,weight=0,minsize=125)
    controls.columnconfigure(1,weight=1)
    controls.columnconfigure(2,weight=0)
    for selector in (app.detection_algorithm_selector,app.detection_action_selector):selector.grid_configure(sticky='ew')
    # The path diagrams need enough width to show all five stages.
    left=app.left_fault_path_diagram.master.master
    right=app.right_fault_path_diagram.master.master
    adaptive_pair(left.master,left,right)
    # Builder controls and the result inspector stay accessible on laptops.
    builder=app.custom_builder_notebook
    siblings=[child for child in builder.master.grid_slaves() if int(child.grid_info()['column'])==1 and int(child.grid_info()['row'])==2]
    if siblings:
        inspector=siblings[0]
        adaptive_pair(builder.master,builder,inspector,row=2)
        details=list(inspector.grid_slaves())
        empty=section(inspector,'Scenario not executed yet',0)
        app.custom_empty_summary=tk.StringVar(app)
        summary_label(empty,app.custom_empty_summary)
        def multi():return builder.index(builder.select())==1
        run=action_button(empty,'Run Scenario',lambda:app.run_multi_only() if multi() else app.run_custom_only())
        compare=action_button(empty,'Compare vs Baseline',lambda:app.compare_multi_vs_baseline() if multi() else app.compare_custom_vs_baseline())
        add=action_button(empty,'Add Event',app.add_multi_event)
        guided=action_button(empty,'Open Guided Cross-Layer Experiment',app.open_guided_experiment)
        for row,button in enumerate((run,compare,add,guided),1):button.grid(row=row,column=0,sticky='w',pady=4)
        app.custom_action_buttons.extend((run,compare,add))
        app.custom_empty_buttons={'run':run,'compare':compare,'add':add,'guided':guided}
        def refresh_empty():
            loaded=app.last_custom_result is not None
            for child in details:
                child.grid() if loaded else child.grid_remove()
            empty.grid_remove() if loaded else empty.grid()
            count=len(app.multi_events)
            staged=(f'{count} staged events configured' if count else 'No staged events configured') if multi() else 'Single-fault scenario configured'
            app.custom_empty_summary.set(staged+'\nDetector: '+app.detection_algorithm_choice.get()+'\nAction: '+app.detection_action_choice.get()+'\n'+
                ('Add 2 to 4 events to run a multi-fault scenario.' if multi() and count<2 else 'Run the scenario to inspect detector and safety outcomes.'))
            ready=not multi() or count>=2
            for button in (run,compare):button.grid() if ready else button.grid_remove()
            add.grid() if multi() and count<2 else add.grid_remove()
            guided.grid() if multi() and count==0 else guided.grid_remove()
        variables=[app.custom_last_run_var,app.custom_status_text,app.detection_algorithm_choice,app.detection_action_choice,app.multi_fault_type,app.multi_start_ms,app.multi_parameter]
        for variable in variables:variable.trace_add('write',lambda *_:app.after_idle(refresh_empty))
        builder.bind('<<NotebookTabChanged>>',lambda _:app.after_idle(refresh_empty),add='+')
        refresh_empty()
        app.custom_empty_state=empty
        app.refresh_custom_empty_state=refresh_empty
    # Tables keep their own horizontal scrollbar; plot selectors stay in view.
    table_card=app.batch_table.master.master
    plot_card=app.batch_plot.master.master
    if table_card.master is plot_card.master:adaptive_pair(table_card.master,table_card,plot_card)
    responsive_labels(app)


def comparison_run_label(result, fallback):
    """Expose recorded cross-layer fault metadata without relabeling scientific rows."""
    if not result or not result.get('raw_rows'):
        return fallback, False
    first=result['raw_rows'][0]
    if first.get('cross_layer_fault_enabled') != '1':
        return fallback, False
    model=first.get('cross_layer_fault_model') or 'N/A'
    summary=result.get('summary_row',{})
    temperature=summary.get('max_coolant_temp_c') or 'N/A'
    state=summary.get('final_safe_state_label') or 'N/A'
    return f'{model} (campaign: {fallback}) · maximum coolant: {temperature} °C · final safe state: {state}', True


def comparison_key_difference(verdict, cross_layer_results=None):
    """Quote an existing verdict line; legacy verdicts cannot classify new faults."""
    if cross_layer_results:
        values=[(cross_layer_results.get(side) or {}).get('summary_row',{}).get('max_coolant_temp_c') or 'N/A' for side in ('left','right')]
        return f'Recorded maximum coolant: left {values[0]} °C; right {values[1]} °C.'
    lines=[line.strip() for line in verdict.splitlines() if line.strip()]
    return lines[0] if lines else 'N/A · Load both cases to inspect their comparison.'


def split_metric_detail(value):
    main, _, detail=value.partition('\n')
    return main,detail


def sweep_metric_values(rows, summary):
    values={name:'N/A' for name in ('Best Coverage','Best Median Latency','Hybrid Coverage','Hybrid Median Latency','Clean Alarms')}
    if not rows:return values
    for title,key,maximum,unit in (('Best Coverage','coverage_percent',True,'%'),('Best Median Latency','median_latency_ms',False,' ms')):
        text=extrema(rows,key,'detector_id',maximum)
        if text!='N/A':
            number,names=text.split(' · ',1)
            labels={str(row.get('detector_id')):str(row.get('detector_name') or row.get('detector_label') or str(row.get('detector_id','N/A')).replace('_',' ').title()) for row in rows}
            names=names.removesuffix(' (tie)')
            values[title]=number+unit+'\n'+' / '.join(labels.get(name,name) for name in names.split(', '))
    for title in ('Hybrid Coverage','Hybrid Median Latency','Clean Alarms'):
        values[title]=summary[title].get() or 'N/A'
    return values
