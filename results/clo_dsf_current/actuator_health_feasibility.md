# Actuator idle-health feasibility: STOP, no extension

## Scope and decision

Read-only scientific audit of the retained triplex validation's33 missed actuators; no simulations rerun, no new validation or unseen. Exactly33 records join the locked validation manifest. All report initially_excited=0, actuator_excited=0 during the active-fault interval, and plant_manifestation=0. Composition:12 transient,12 intermittent,9 permanent. Remaining33 are a subset of the53 initially-unexcited actuators; the20 later-excited detections are not reclassified as misses.

Decision bins are mutually exclusive: idle-health observable0; excitation-required33; wholly unsupported modeled fault cases0. The last number means all33 have an explicit performance-fault model; it does NOT mean their electrical cause is supported. Electrical-health coverage for these33 is unsupported. Fewer than5–10 recoverable cases => STOP before implementation.

## Physical semantics and exhaustive case classification

Category counts A/B/C/D/E/F =0/0/0/0/33/0. Every individual case is recorded in actuator_health_miss_classification.csv. E means generic pump performance/authority loss, not a claim that a particular hydraulic mechanism is simulated. No winding damage, electrical open circuit, driver failure or specific mechanical defect can be inferred from the label.

`src/fault_injection.c` sets pump_scale to the event parameter. `src/actuators.c:actuators_step` multiplies the clamped requested pump action by that scale. `src/thermal_plant.c` uses7.5*pump_actual as cooling. Thus a(q,s)=clamp(q)*s and da/ds=clamp(q); when q=0, both healthy and faulty a=0 for any s. There is no hidden electrical-current, winding-resistance, rotor-speed, pressure or driver-temperature state altered by s. Existing source/runtime capture confirms the performance signal, not independent electrical telemetry. This is a structural indistinguishability result; magnitude or fault duration cannot reveal the scale at zero command.

Excitation is a necessary condition here, not a guarantee of detection for every weak or short fault. Normal future controller demand could reveal a persistent fault without a diagnostic command; a transient that ends before demand may remain permanently unobserved. No actuator is commanded for this study. Offline use of the manifest classifies model semantics; it is never a detector input.

|Category|Cases|Diagnostic while command=0|
|---|---:|---|
|A electrical driver failure|0|YES for independently powered, covered internal status failures; not every output fault. Unsupported root cause for these cases.|
|B open/short/continuity|0|YES on suitable off-state diagnostic hardware, often with non-motion bias current; otherwise ONLY WITH ACTIVE TEST. No such impedance fault is modeled here.|
|C winding/electrical degradation|0|ONLY WITH ACTIVE TEST/measurement for resistance or insulation change; complete open/short can fall under B. No quantitative winding model here.|
|D mechanical degradation|0|NO general passive idle signature; ONLY WITH mechanical excitation for load/rotation-dependent defects. Specific root cause unspecified here.|
|E hydraulic/performance degradation|33|NO at idle in this model; ONLY WITH flow/action excitation.|
|F other|0|Cannot assign coverage without physical semantics.|

## Real driver evidence and limits

TI documents off-state open-load circuits using high-impedance outputs and diagnostic bias; its DRV8847 example uses about100 microamps, described as insufficient to rotate the load. Availability depends on power/state, fault interlocks, topology and settling. This demonstrates feasibility for electrical connectivity faults, not the current performance-scale faults. [TI passive OLD](https://www.ti.com/document-viewer/lit/html/SLVAE49C/GUID-6EA1C407-464C-4405-B6EB-C7C6EE060738).

TI's DRV824x example distinguishes output shorts below100ohms and full-bridge opens above1kilohm via multiple comparator configurations. Such thresholds are device/topology-specific, with a region that cannot be treated as universally healthy or failed. [TI DRV824x off-state diagnostics](https://www.ti.com/document-viewer/lit/html/SLVAE49C/GUID-F9C2AE46-F6AF-4D5F-A08F-0F1D218CD4F8).

Infineon describes off-state open-load sensing using output voltage and bias circuitry. Its circuit guidance notes capacitance charging and leakage affect diagnosis; these prevent instantaneous, universally available status. [Infineon overview](https://www.infineon.com/product-information/power-switches-types/open-load-detection), [circuit/settling guidance](https://community.infineon.com/t5/Knowledge-Base-Articles/Calculate-external-circuitry-for-open-load-detection-in-PROFET-2-12-V/ta-p/1010417).

The following is a feasibility contract, NOT implemented channels or invented calibrated specifications. Exact numeric delays/errors cannot be selected without a device, topology and actuator parameters. No false-positive probability is assumed zero.

|Signal|Availability and covered faults|Latency/uncertainty/false-status constraints|Coverage of33|
|---|---|---|---:|
|Driver status register|Powered, awake, valid bus read; documented UVLO/overtemperature/gate/internal faults only|Device diagnostic delay plus polling/bus delay; reset, latched historical faults, stale reads and bus errors must yield invalid/aged status; fault bit does not establish generic mechanical health|0|
|Off-state open-load|Supported disabled-output topology with enabled bias path; gross disconnected/high-impedance load|Output discharge/RC settling plus specified deglitch and polling; leakage, harness capacitance, thresholds and temperature can cause ambiguous/transient status; unavailable in incompatible modes|0|
|Short-to-ground/supply|Supported comparator sequences and supply conditions; covered low-impedance shorts|Configuration sequence and comparator settling/deglitch; a single comparator result may alias different conditions, requiring multiple settings; no healthy inference from unavailable test|0|
|Winding continuity/resistance|Bias-current measurement with defined circuit path; gross discontinuity or measurable impedance change|Settling, ADC resolution, offsets, lead resistance and copper temperature confound weak changes; requires an electrical winding model and characterized bounds|0|
|Driver overtemperature|Powered on-die temperature comparator; driver thermal fault only|Thermal dynamics plus debounce/hysteresis; warm environment/prior operation can assert genuine temperature status unrelated to pump efficiency; sleep may disable sensing|0|
|Motor current|Powered calibrated current sensor and defined current path; energized overload/underload or certain leakage conditions|ADC bandwidth/filter delay; offset/noise dominate near zero; zero commanded current is normal in both current cases. No modeled leakage or electrical defect|0|
|Back-EMF|Motor rotating/coasting and accessible high-impedance measurement interval|Commutation/blanking and sampling delay; magnitude proportional to speed, low-speed noise/offset; zero EMF at rest cannot diagnose generic degradation. No coasting/rotor model here|0|
|Tachometer/pump speed|Powered sensor and motion; detects missing/abnormal rotation under expected action|Pulse-window latency grows at low speed; missing pulses at idle are normal; wiring/pulse dropouts are sensor faults. Speed alone may not detect hydraulic efficiency loss even while moving|0|

Near-passive bias would be permissible only with worst-case current/energy, torque, breakaway and thermal bounds proving no motion or measurable cooling/heating change for the chosen actuator. The100microamp example is not a universal guarantee. No such driver/winding/inertia/thermal parameters exist in this repository, and adding them cannot retroactively convert pump_scale into electrical failures.

## Existing feedback caution

`src/actuators.c:update_fan_actuator_feedback` contains a legacy self_test_gap derived from the FAN_STUCK_OFF injected mode. It is fan-specific and not independent physical proof of idle health. All33 misses are pump faults. Do not copy this into a pump fault-present bit or cite it as recoverable coverage. Leave legacy code and evidence untouched.

## Outcome

Selected diagnostic NONE; implementation not justified. Additional TRAIN/CALIBRATION detections, benign alarms and wrong origins: not evaluated because no provider or campaign was implemented. Existing initially-unexcited validation detection20/53 is unchanged; the targeted33 stay undetected. Plant perturbation NONE. No retained detector, control, thermal model, thresholds, fusion or GUI changes. No full regression is warranted for documentation/CSV-only additions. Recommend preserve the limitation and freeze the retained Triplex; electrical-driver diagnostics would require a separately justified physical model and fault population, not a fix for these33.
