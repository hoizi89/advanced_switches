# Advanced Switches

Home Assistant integration for smart plug session tracking with energy monitoring and scheduling.

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)

## What it does

Turns any switch with power/energy sensors (smart plugs, Shelly relays, in-wall switches) into a smart device tracker:
- Detects when device is running (active) or in standby
- Counts sessions/cycles and tracks energy per session
- Shows daily and total statistics
- Optional: Only allow operation at certain times (schedule)
- Optional: Auto-off after X minutes

**Use cases:** Washing machine, dryer, sauna, air compressor, pump, etc.

## Requirements

A smart plug with:
- Switch entity
- Power sensor (W)
- Energy sensor (kWh)

## Installation

**HACS:** Search for "Advanced Switches" → Install → Restart HA

**Manual:** Copy `custom_components/advanced_switches` to your config folder → Restart HA

## Setup

Settings → Devices & Services → Add Integration → "Advanced Switches"

Choose operating mode:
- **Simple Mode** - Two states: OFF / ACTIVE (e.g., compressor, pump)
- **Standby Mode** - Three states: OFF / STANDBY / ACTIVE (e.g., washing machine, sauna)

## Parameters

### Simple Mode

| Parameter | Default | Description |
|-----------|---------|-------------|
| Active Threshold (W) | 50 | Power above = active |
| On Delay (s) | 3 | Wait before OFF → ACTIVE |
| Off Delay (s) | 5 | Wait before ACTIVE → OFF |
| Min Active Duration (s) | 10 | Shorter cycles are ignored |
| Power Smoothing (s) | 0 | Moving average (0 = off) |

### Standby Mode

| Parameter | Default | Description |
|-----------|---------|-------------|
| Standby Threshold (W) | 5 | Power above = standby |
| Active Threshold (W) | 1000 | Power above = active |
| On Delay (s) | 3 | Wait before state changes |
| Active/Standby Delay (s) | 5 | Wait for ACTIVE ↔ STANDBY |
| Session End Grace (s) | 120 | Prevents false session ends |
| Min Session Duration (s) | 60 | Shorter sessions are ignored |
| Power Smoothing (s) | 0 | Moving average (0 = off) |
| Session End on STANDBY | off | See below |

#### Session End on STANDBY

Controls when a session is counted as complete:

| Setting | Behavior | Use Case |
|---------|----------|----------|
| **OFF** (default) | Session continues during ACTIVE↔STANDBY cycling, ends only at OFF | Sauna, oven (heating cycles) |
| **ON** | Each ACTIVE phase is a separate session | Washing machine, dishwasher |

**Example - Washing Machine (ON):**
```
Load 1: STANDBY → ACTIVE (30min) → STANDBY = Session 1 ✓
Load 2: STANDBY → ACTIVE (45min) → STANDBY = Session 2 ✓
→ 2 sessions counted
```

**Example - Sauna (OFF):**
```
ACTIVE (heating) → STANDBY → ACTIVE → STANDBY → ... → OFF
→ 1 session counted (entire usage)
```

### Schedule (Optional)

| Parameter | Default | Description |
|-----------|---------|-------------|
| Enable Schedule | off | Turn on scheduling |
| Start Time | 06:00 | Allowed from |
| End Time | 22:00 | Allowed until |
| Days | Mon-Sun | Allowed days |

Outside allowed times: switch turns off and blocks.

### Auto-Off (Optional)

Turns off the switch automatically X minutes after it was turned on.

| Parameter | Default | Description |
|-----------|---------|-------------|
| Enable Auto-Off | off | Turn on auto-off |
| Minutes | 60 | Turn off X minutes after switch turns on |

### Power Smoothing

For noisy sensors (e.g., washing machine fluctuating 0.3-3W in standby):
- Set Power Smoothing to 30-60 seconds
- Smoothed value is used for state detection
- Peak power still uses raw values

## Created Entities

**Main:**
- `sensor.<name>_state` - off / standby / active / blocked
- `binary_sensor.<name>_active` - true when active
- `binary_sensor.<name>_on` - true when on (standby or active)

**Statistics:**
- `sensor.<name>_sessions_total` - total count
- `sensor.<name>_sessions_today` - today's count
- `sensor.<name>_energy_today` - kWh today
- `sensor.<name>_energy_total` - kWh total

**Last Session:**
- `sensor.<name>_last_session_duration`
- `sensor.<name>_last_session_energy`
- `sensor.<name>_last_session_peak_power`

**Current Session:**
- `sensor.<name>_current_session_duration`
- `sensor.<name>_current_session_energy`
- `sensor.<name>_current_session_peak_power`

**Averages:**
- `sensor.<name>_avg_session_duration`
- `sensor.<name>_avg_session_energy`

**Schedule:**
- `binary_sensor.<name>_schedule_blocked`
- `binary_sensor.<name>_schedule_turned_off`

**Auto-Off:**
- `sensor.<name>_auto_off_remaining` - countdown ("in 59 min" / "Inaktiv")

**Other:**
- `sensor.<name>_smoothed_power` - diagnostic

## Example Configs

**Washing Machine:**
- Standby Threshold: 1W
- Active Threshold: 10W
- Session End on STANDBY: ON (count each wash cycle)
- Power Smoothing: 30s

**Sauna:**
- Standby Threshold: 5W
- Active Threshold: 1000W
- Session End on STANDBY: OFF (heating cycles count as one session)
- Session End Grace: 120s

**Compressor (daytime only):**
- Active Threshold: 50W
- Schedule: 07:00-20:00, Mon-Fri

## License

MIT
