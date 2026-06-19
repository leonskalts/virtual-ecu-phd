# Driving Environment Profiles

The virtual ECU keeps the built-in thermal plant as the default driving
environment. If no profile is provided, the simulator uses the existing
hardcoded thermal phases:

- `warmup`
- `highway_load`
- `urban_traffic`
- `hot_idle`

This preserves the default experiment behavior and predefined study behavior.

## Custom Driving Profile Mode

Custom Driving Profile mode is optional. It is enabled only when the simulator
is launched with `--driving-profile <path>` or when the Tkinter GUI exports and
uses a custom profile from the Custom Faults page.

The profile controls the input conditions used by the existing thermal
equations. It does not introduce a second thermal model.

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

Example:

```csv
start_ms,end_ms,vehicle_speed_kph,engine_load,ambient_temp_c,external_airflow_factor,road_slope_percent
0,20000,100,0.45,30,0.4,0
20000,40000,80,0.50,30,0.3,0
40000,60000,30,0.65,30,0.1,4
```

## GUI Export

In the Tkinter GUI, open Custom Faults and use Driving / Environment Conditions.
When Custom Driving Profile is selected and applied, the GUI writes:

```text
profiles/driving/latest_gui_driving_profile.csv
```

Custom Fault runs then pass that file to the simulator with `--driving-profile`.
If the latest custom run used a custom profile, the Runtime Study page's custom
matrix runner reuses that profile. Predefined runtime studies continue to use
Default Thermal Plant mode.

## Terminal Usage

```sh
./virtual_ecu logs/driving_profile_test.csv custom fan_stuck_off 75000 0 permanent 0.0 \
  --detector kalman_filter \
  --detector-action observe_only \
  --driving-profile profiles/driving/test_profile.csv
```

Omit `--driving-profile` to use the Default Thermal Plant.

## Simplifications

This is a controllable research model for virtual ECU experiments. It is not a
calibrated production vehicle model and is not a real aerodynamics model.

- `external_airflow_factor` is a simplified extra cooling modifier.
- `road_slope_percent` is a simplified effective-load modifier.
- No Beaufort scale or real wind model is used.
