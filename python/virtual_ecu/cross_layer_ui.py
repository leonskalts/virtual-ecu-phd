"""Pure UI field visibility and command adapter; delegates to frozen fault_options."""
from .cross_layer_safety import MODEL_TARGETS, fault_options

DEFAULTS = {'Fault Layer': 'memory', 'Fault Model': 'bit_flip', 'Fault Target': 'control_target_register', 'Behavior': 'transient', 'Start Time (ms)': '45000', 'Duration (ms)': '100', 'Bit Index': '5', 'Seed': '42', 'Intermittent ON (ms)': '100', 'Intermittent OFF (ms)': '500', 'Stuck Polarity': '1', 'Communication Delay (ms)': '300', 'Drop Count': '3', 'Drop Every N Updates': '0', 'Replay Age (ms)': '500', 'Task Delay (ms)': '200', 'FTTI (ms)': '5000', 'Warning Threshold (°C)': '108', 'Critical Threshold (°C)': '115', 'Max Critical Exposure (ms)': '1000', 'Timing Monitor': 'Disabled', 'Communication Safety Response': 'Observe Only'}
DEFAULTS.update({"Sensor Bias (°C)": "6.0", "Pump Effectiveness": "0.45"})
UI_MODELS = {**MODEL_TARGETS, "sensor_bias": ("sensing_control", "coolant_sensor"),
             "pump_degraded": ("actuator", "pump"), "fan_stuck_off": ("actuator", "fan")}
LAYER_LABELS = {"Memory": "memory", "Timing": "timing", "Communication": "communication",
                "Sensor / Control": "sensing_control", "Actuator": "actuator"}
CONTRACT = ("FTTI (ms)", "Warning Threshold (°C)", "Critical Threshold (°C)", "Max Critical Exposure (ms)")
MODEL_FIELDS = {
    "bit_flip": ("Bit Index",), "stuck_bit": ("Bit Index", "Stuck Polarity"),
    "deadline_miss": (), "task_delay": ("Task Delay (ms)",),
    "delayed_update": ("Communication Delay (ms)",),
    "dropped_update": ("Drop Count", "Drop Every N Updates"),
    "replayed_sample": ("Replay Age (ms)",), "sensor_bias": ("Sensor Bias (°C)",),
    "pump_degraded": ("Pump Effectiveness",), "fan_stuck_off": (),
}


def behaviors(model):
    return ("transient", "intermittent", "permanent") if model in MODEL_TARGETS else ("transient", "permanent")


def visible_fields(values, mode="Guided", contract_open=False):
    model, behavior = values["Fault Model"], values["Behavior"]
    fields = {"Fault Layer", "Fault Model", "Behavior", "Fault Target", "Start Time (ms)", *MODEL_FIELDS[model]}
    if behavior != "permanent" and not (model == "deadline_miss" and behavior == "transient"):
        fields.add("Duration (ms)")
    if behavior == "intermittent":
        fields.update(("Intermittent ON (ms)", "Intermittent OFF (ms)"))
    # Seed and both independent monitor modes remain accessible; hiding never resets them.
    fields.update(("Timing Monitor", "Communication Safety Response"))
    if mode == "Advanced": fields.add("Seed")
    if mode == "Advanced" or contract_open: fields.update(CONTRACT)
    return fields


def backend_request(values):
    model = values["Fault Model"]
    if model not in UI_MODELS or values["Behavior"] not in behaviors(model):
        raise ValueError("Select a supported fault model and behavior")
    if model in MODEL_TARGETS:
        positional = ["baseline"]
        options = _cross_layer_options(values)
    else:
        parameter = values["Sensor Bias (°C)"] if model == "sensor_bias" else values["Pump Effectiveness"] if model == "pump_degraded" else "0.0"
        positional = ["custom", model, str(int(values["Start Time (ms)"])), str(int(values["Duration (ms)"])), values["Behavior"], parameter]
        options = ["--seed", str(int(values["Seed"])), "--cross-layer-monitor", "on"]
        options += _safety_options(values)
    return positional, options


def _cross_layer_options(values):
    options = fault_options(
            values["Fault Model"],
            start_ms=int(values["Start Time (ms)"]),
            duration_ms=int(values["Duration (ms)"]),
            bit_index=int(values["Bit Index"]),
            seed=int(values["Seed"]),
            behavior=values["Behavior"],
            intermittent_on_ms=int(values["Intermittent ON (ms)"]),
            intermittent_off_ms=int(values["Intermittent OFF (ms)"]),
            stuck_polarity=int(values["Stuck Polarity"]),
            communication_delay_ms=int(values["Communication Delay (ms)"]),
            drop_count=int(values["Drop Count"]),
            drop_every_n_updates=int(values["Drop Every N Updates"]),
            replay_age_ms=int(values["Replay Age (ms)"]),
            task_delay_ms=int(values["Task Delay (ms)"]),
        )
    return options + _safety_options(values)


def _safety_options(values):
    options = []
    options += ["--hazard-monitor", "on", "--ftti-ms", values["FTTI (ms)"],
                "--hazard-warning-c", values["Warning Threshold (°C)"],
                "--hazard-critical-c", values["Critical Threshold (°C)"],
                "--max-critical-exposure-ms", values["Max Critical Exposure (ms)"]]
    options += ["--timing-monitor", values["Timing Monitor"].lower().replace(" ", "_"),
                "--communication-safety-response", values["Communication Safety Response"].lower().replace(" ", "_")]

    return options


def shown(value):
    return "N/A" if value in (None, "", "N/A", "-1", -1) else str(value)


def interpretation(row):
    parts = []
    for key, label in (("detected", "Detected"), ("plant_manifestation", "Plant affected"),
                       ("hazard_entered", "Hazard entered"), ("safe_state_reached", "Safe state applied"),
                       ("containment_success", "Containment")):
        value = row.get(key)
        text = "yes" if str(value).lower() in ("1", "true") else "no" if str(value).lower() in ("0", "false") else "N/A"
        parts.append(f"{label}: {text}")
    return ". ".join(parts) + ". Values describe loaded evidence; safe-state application alone does not prove containment."


def propagation_states(row):
    stages = (("Fault origin", "fault_injection_ms"), ("Internal / ECU", "propagation_internal_ms"),
              ("Control", "propagation_control_ms"), ("Actuator", "propagation_actuator_realization_ms"),
              ("Plant", "propagation_plant_ms"), ("Hazard entry", "hazard_entry_ms"))
    return [(label, "reached" if shown(row.get(key)) != "N/A" else "N/A", shown(row.get(key))) for label, key in stages]
