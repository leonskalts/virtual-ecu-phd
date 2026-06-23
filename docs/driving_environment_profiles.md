# Driving Environment Profiles

The virtual ECU keeps the built-in thermal plant as the default driving
environment. If no profile or duration option is provided, the simulator uses
the existing hardcoded thermal phases and the existing default duration:

- `warmup`
- `highway_load`
- `urban_traffic`
- `hot_idle`

This preserves default experiment behavior and predefined runtime-study
behavior.

## Duration Modes

Default duration mode is used when `--simulation-duration-ms` is omitted. The
run uses the compiled default simulation duration.

Custom duration mode is enabled only with:

```sh
--simulation-duration-ms <duration_ms>
```

The value must be between 1000 ms and 3600000 ms. Summary CSV files report:

- `simulation_duration_mode`: `default` or `custom`
- `simulation_duration_ms`: actual duration used

## Custom Driving Profile Mode

Custom Driving Profile mode is optional. It is enabled only when the simulator
is launched with `--driving-profile <path>` or when the Tkinter GUI exports and
uses a custom profile from the Custom Faults page.

The profile controls the input conditions used by the existing thermal
equations. It does not introduce a second thermal model.

When `--driving-profile` is used without `--simulation-duration-ms`, the legacy
profile behavior is preserved. When both options are used, the profile must
cover the full simulation interval exactly.

## CSV Schema

Profiles use CSV with this header:

```csv
start_ms,end_ms,vehicle_speed_kph,engine_load,ambient_temp_c,external_airflow_factor,road_slope_percent
```

Columns:

- `start_ms`, `end_ms`: segment interval in milliseconds.
- `vehicle_speed_kph`: vehicle speed in km/h, non-negative.
- `engine_load`: normalized engine load in `[0.0, 1.0]`.
- `ambient_temp_c`: ambient temperature in degrees C, expected `[-40, 80]`.
- `external_airflow_factor`: simplified extra cooling factor in `[0.0, 1.0]`.
- `road_slope_percent`: simplified grade/load modifier in `[-20, 20]`.

Valid 300-second profile:

```csv
start_ms,end_ms,vehicle_speed_kph,engine_load,ambient_temp_c,external_airflow_factor,road_slope_percent
0,100000,100,0.45,30,0.4,0
100000,200000,80,0.60,32,0.3,0
200000,300000,20,0.90,38,0.0,6
```

Invalid for 300 seconds because 200000-300000 ms is uncovered:

```csv
start_ms,end_ms,vehicle_speed_kph,engine_load,ambient_temp_c,external_airflow_factor,road_slope_percent
0,100000,100,0.45,30,0.4,0
100000,200000,80,0.60,32,0.3,0
```

## Strict Coverage

Strict coverage is enforced when Custom Driving Profile mode is combined with a
custom simulation duration.

Rules:

- first segment must start at 0 ms
- every segment must have `end_ms > start_ms`
- segments must not overlap
- segments must not have gaps
- final segment must end exactly at `simulation_duration_ms`
- profiles ending before or after the selected duration are rejected

Errors report the uncovered or overlapping interval.

## GUI Export

In the Tkinter GUI, open Custom Faults and use Driving / Environment Conditions.
When Custom Driving Profile is selected and applied, the GUI writes:

```text
profiles/driving/latest_gui_driving_profile.csv
```

The GUI profile editor includes Simulation Duration [s]. Apply validates full
coverage and blocks profiles with gaps, overlaps, early endings, or segments
past the selected duration.

The Extend Last Segment to Duration button explicitly adds a visible segment
from the last end time to the selected duration by copying the last segment's
driving/environment values. It is never applied silently.

Custom Fault runs pass:

```sh
--driving-profile profiles/driving/latest_gui_driving_profile.csv
--simulation-duration-ms <duration_ms>
```

If the latest custom run used a custom profile and duration, the Runtime Study
page's custom matrix runner reuses both. Predefined runtime studies continue to
use Default Thermal Plant mode and default duration.

## Terminal Usage

```sh
./virtual_ecu logs/duration_300s_test.csv custom fan_stuck_off 75000 0 permanent 0.0 \
  --detector kalman_filter \
  --detector-action observe_only \
  --driving-profile profiles/driving/example_driving_profile.csv \
  --simulation-duration-ms 300000
```

Omit `--driving-profile` and `--simulation-duration-ms` to use the Default
Thermal Plant and default duration.

## Simplifications

This is a controllable research model for virtual ECU experiments. It is not a
calibrated production vehicle model and is not a real aerodynamics model.

- `external_airflow_factor` is a simplified extra cooling modifier.
- `road_slope_percent` is a simplified effective-load modifier.
- No Beaufort scale or real wind model is used.
