# Smart Plug Tracker

Home Assistant Integration zur Erstellung virtueller Geräte aus Smart-Steckdosen mit Energiemessung.

## Features

- **Session/Zyklus-Tracking**: Erkennt automatisch Start und Ende von Betriebszyklen
- **Energie pro Session**: Berechnet den Verbrauch pro Session/Zyklus
- **Tages- und Gesamtstatistiken**: Sessions und Energie heute/gesamt
- **Zwei Betriebsmodi**:
  - **Simple Mode**: OFF/ACTIVE (z.B. Luftkompressor)
  - **Standby Mode**: OFF/STANDBY/ACTIVE (z.B. Sauna, Waschmaschine)
- **Mehrere Instanzen**: Beliebig viele Geräte parallel

## Voraussetzungen

Eine Smart-Steckdose mit:
- Switch Entity (zum Ein-/Ausschalten)
- Power Sensor (Watt)
- Energy Sensor (kWh, total_increasing)

## Installation

### HACS (empfohlen)

1. HACS öffnen
2. "Integrationen" → "Custom Repositories"
3. URL hinzufügen: `https://github.com/hoizi89/smart_plug_tracker`
4. Integration installieren
5. Home Assistant neu starten

### Manuell

1. `custom_components/smart_plug_tracker` nach `config/custom_components/` kopieren
2. Home Assistant neu starten

## Konfiguration

1. Einstellungen → Geräte & Dienste → Integration hinzufügen
2. "Smart Plug Tracker" suchen
3. Gerät konfigurieren:
   - **Name**: z.B. "Sauna", "Kompressor", "Waschmaschine"
   - **Switch/Power/Energy Entities**: Auswählen
   - **Modus**: Simple oder Standby

### Simple Mode (Kompressor, etc.)

| Parameter | Default | Beschreibung |
|-----------|---------|--------------|
| `active_threshold_w` | 50 | Power >= X = aktiv |
| `on_delay_s` | 3 | Verzögerung OFF→ACTIVE |
| `off_delay_s` | 5 | Verzögerung ACTIVE→OFF |
| `min_active_s` | 10 | Mindestdauer für Zyklus |

### Standby Mode (Sauna, Waschmaschine, etc.)

| Parameter | Default | Beschreibung |
|-----------|---------|--------------|
| `standby_threshold_w` | 5 | Power >= X = standby |
| `active_threshold_w` | 1000 | Power >= X = aktiv |
| `on_delay_s` | 3 | Verzögerung für Zustandswechsel |
| `off_delay_s` | 5 | Verzögerung STANDBY→OFF |
| `session_end_grace_s` | 120 | Grace Period gegen Taktung |
| `min_session_s` | 60 | Mindestdauer für Session |

## Erzeugte Entities

| Entity | Beschreibung |
|--------|--------------|
| `switch.<name>_power` | Proxy zur Steckdose |
| `sensor.<name>_state` | off/standby/active |
| `binary_sensor.<name>_active` | True bei active |
| `binary_sensor.<name>_on` | True bei standby/active (nur Standby Mode) |
| `sensor.<name>_sessions_total` | Gesamt-Zähler |
| `sensor.<name>_sessions_today` | Sessions heute |
| `sensor.<name>_last_session_duration` | Letzte Dauer |
| `sensor.<name>_last_session_energy` | Letzte Energie (kWh) |
| `sensor.<name>_energy_today` | Energie heute (kWh) |

## Beispiel-Konfigurationen

### Sauna (Standby Mode)
```
standby_threshold_w: 5
active_threshold_w: 1000
session_end_grace_s: 120   # Heiz-Taktung ignorieren
min_session_s: 60
```

### Waschmaschine (Standby Mode)
```
standby_threshold_w: 3
active_threshold_w: 10
session_end_grace_s: 300   # 5 Min für Pausenphasen
min_session_s: 60
```

### Kompressor (Simple Mode)
```
active_threshold_w: 50
on_delay_s: 3
off_delay_s: 5
min_active_s: 10
```

## Benachrichtigungen

Die Integration erstellt keine Benachrichtigungen. Für "Waschmaschine fertig" etc. eine Automation erstellen:

```yaml
trigger:
  - platform: state
    entity_id: sensor.waschmaschine_state
    from: "active"
    to: "standby"
action:
  - service: notify.mobile_app
    data:
      title: "Waschmaschine fertig!"
      message: "Bitte Wäsche abholen"
```

## Lizenz

MIT License
