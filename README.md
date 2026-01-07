# Advanced Switches

Home Assistant integration for creating virtual devices from smart plugs with energy monitoring, session tracking, and scheduling.

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)

## Features

- **Session/Cycle Tracking**: Automatically detects start and end of operating cycles
- **Energy per Session**: Calculates energy consumption per session/cycle
- **Daily and Total Statistics**: Sessions and energy today/total
- **Two Operating Modes**:
  - **Simple Mode**: OFF/ACTIVE (e.g., air compressor, pump)
  - **Standby Mode**: OFF/STANDBY/ACTIVE (e.g., sauna, washing machine, dryer)
- **Power Smoothing**: Moving average for noisy power sensors (optional)
- **Schedule Control**: Allow devices only at certain times (e.g., compressor only during daytime)
- **Auto-Off Timer**: Automatically turn off after a set duration
- **Multiple Instances**: Unlimited devices in parallel

## Requirements

A smart plug with:
- Switch Entity (for on/off control)
- Power Sensor (Watt)
- Energy Sensor (kWh, total_increasing)

## Installation

### HACS (Recommended)

1. Open HACS
2. Click "Integrations"
3. Search for "Advanced Switches"
4. Install the integration
5. Restart Home Assistant

### Manual

1. Copy `custom_components/advanced_switches` to your `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Settings → Devices & Services → Add Integration
2. Search for "Advanced Switches"
3. Configure the device:
   - **Name**: e.g., "Sauna", "Compressor", "Washing Machine"
   - **Switch/Power/Energy Entities**: Select from your entities
   - **Mode**: Simple or Standby
   - **Schedule**: Optionally enable time-based control

### Simple Mode (Compressor, Pump, etc.)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `active_threshold_w` | 50 | Power >= X = active |
| `on_delay_s` | 3 | Delay for OFF→ACTIVE |
| `off_delay_s` | 5 | Delay for ACTIVE→OFF |
| `min_active_s` | 10 | Minimum duration to count as cycle |
| `power_smoothing_s` | 0 | Moving average window (0 = disabled) |

### Standby Mode (Sauna, Washing Machine, etc.)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `standby_threshold_w` | 5 | Power >= X = standby |
| `active_threshold_w` | 1000 | Power >= X = active |
| `on_delay_s` | 3 | Delay for state changes |
| `active_standby_delay_s` | 5 | Delay for ACTIVE↔STANDBY |
| `session_end_grace_s` | 120 | Grace period to prevent false session ends |
| `min_session_s` | 60 | Minimum duration to count as session |
| `power_smoothing_s` | 0 | Moving average window (0 = disabled) |

### Power Smoothing

For devices with noisy power sensors (e.g., washing machines fluctuating between 0.3W and 3W in standby), enable power smoothing:

- Set `power_smoothing_s` to the averaging window in seconds (e.g., 30-60)
- The smoothed power value is used for state detection
- Peak power tracking still uses raw values
- A diagnostic sensor shows the smoothed power value

### Schedule Control (Optional)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `schedule_enabled` | false | Enable scheduling |
| `schedule_start` | 06:00 | Start time (allowed from) |
| `schedule_end` | 22:00 | End time (allowed until) |
| `schedule_days` | Mon-Sun | Allowed weekdays |

**Example: Compressor only during daytime:**
- `schedule_enabled`: true
- `schedule_start`: 07:00
- `schedule_end`: 20:00
- `schedule_days`: Mon-Fri

Outside allowed times:
- Switch is automatically turned off
- Turning on is blocked
- State shows "blocked"

### Auto-Off Timer (Optional)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `auto_off_enabled` | false | Enable auto-off |
| `auto_off_minutes` | 60 | Turn off after X minutes |

Useful for devices that should not run indefinitely.

## Created Entities

| Entity | Description |
|--------|-------------|
| `sensor.<name>_state` | off/standby/active/blocked |
| `binary_sensor.<name>_active` | True when active |
| `binary_sensor.<name>_on` | True when standby/active (Standby Mode only) |
| `binary_sensor.<name>_schedule_blocked` | True when blocked by schedule |
| `binary_sensor.<name>_schedule_turned_off` | True when turned off by schedule |
| `sensor.<name>_sessions_total` | Total session counter |
| `sensor.<name>_sessions_today` | Sessions today |
| `sensor.<name>_last_session_duration` | Last session duration |
| `sensor.<name>_last_session_energy` | Last session energy (kWh) |
| `sensor.<name>_last_session_peak_power` | Last session peak power (W) |
| `sensor.<name>_energy_today` | Energy today (kWh) |
| `sensor.<name>_energy_total` | Total energy (kWh) |
| `sensor.<name>_current_session_duration` | Current session duration |
| `sensor.<name>_current_session_energy` | Current session energy (kWh) |
| `sensor.<name>_current_session_peak_power` | Current session peak power (W) |
| `sensor.<name>_avg_session_duration` | Average session duration |
| `sensor.<name>_avg_session_energy` | Average session energy (kWh) |
| `sensor.<name>_auto_off_at` | Auto-off timestamp (if enabled) |
| `sensor.<name>_smoothed_power` | Smoothed power (diagnostic) |

## Example Configurations

### Sauna (Standby Mode)
```yaml
standby_threshold_w: 5
active_threshold_w: 1000
session_end_grace_s: 120   # Ignore heating cycles
min_session_s: 60
```

### Washing Machine (Standby Mode)
```yaml
standby_threshold_w: 1
active_threshold_w: 10
session_end_grace_s: 300   # 5 min for pause phases
min_session_s: 60
power_smoothing_s: 30      # Smooth noisy readings
```

### Compressor with Night Mode (Simple Mode)
```yaml
active_threshold_w: 50
on_delay_s: 3
off_delay_s: 5
min_active_s: 10
schedule_enabled: true
schedule_start: "07:00"
schedule_end: "20:00"
```

## Notifications

The integration does not create notifications. For "Washing machine finished" etc., create an automation:

```yaml
trigger:
  - platform: state
    entity_id: sensor.washing_machine_state
    from: "active"
    to: "standby"
action:
  - service: notify.mobile_app
    data:
      title: "Washing Machine Finished!"
      message: "Please collect your laundry"
```

## State Machine

### Simple Mode
```
    ┌───────┐  power >= threshold  ┌────────┐
    │  OFF  │ ──────────────────► │ ACTIVE │
    └───────┘  for on_delay_s      └────────┘
        ▲                              │
        │  power < threshold           │
        │  for off_delay_s             │
        └──────────────────────────────┘

Cycle = OFF → ACTIVE → OFF (if duration >= min_active_s)
```

### Standby Mode
```
                      power >= active_threshold
                ┌─────────────────────────────────┐
                │                                 │
                ▼                                 │
            ┌────────┐                        ┌───────┐
            │ ACTIVE │ ◄──────────────────────│  OFF  │
            └────────┘   power >= standby      └───────┘
                │                                  ▲
                │ power < active                   │
                │ (but >= standby)                 │
                ▼                                  │
            ┌─────────┐                            │
            │ STANDBY │                            │
            └─────────┘                            │
                │                                  │
                │ power < standby_threshold        │
                │ for session_end_grace_s          │
                └──────────────────────────────────┘

Session = OFF → (STANDBY|ACTIVE) → ... → OFF
  - ACTIVE↔STANDBY transitions do NOT end session
  - Session ends only when power < standby for grace period
  - Only counted if duration >= min_session_s
```

## License

MIT License
