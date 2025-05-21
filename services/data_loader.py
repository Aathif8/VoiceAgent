import pandas as pd
from datetime import datetime, timedelta
import json

file_path = "../data/appointments.json"

def normalize_date(date_str: str) -> str:
    today = datetime.today()
    if not date_str:
        return None
    date_str = date_str.lower()
    if "tomorrow" in date_str:
        return (today + timedelta(days=1)).strftime('%d.%m.%Y')
    elif "today" in date_str:
        return today.strftime('%d.%m.%Y')
    try:
        parsed = datetime.strptime(date_str, "%d %B %Y")  # Example: 20 May 2025
        return parsed.strftime('%d.%m.%Y')
    except:
        return None

def normalize_time(time_str: str) -> str:
    try:
        parsed = datetime.strptime(time_str.upper(), "%I:%M%p")
        return parsed.strftime("%I:%M%p")
    except:
        return None

def add_appointment(new_appointment: dict) -> str:
    import json
    from datetime import datetime

    json_file_path = "../data/appointments.json"

    try:
        with open(json_file_path, "r") as f:
            appointments = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        appointments = []

    new_date = datetime.strptime(new_appointment['DATE'], '%d.%m.%Y').date()
    new_time = datetime.strptime(new_appointment['TIME'], '%I:%M%p').time()

    for appt in appointments:
        appt_date = datetime.strptime(appt['DATE'], '%d.%m.%Y').date()
        appt_time = datetime.strptime(appt['TIME'], '%I:%M%p').time()

        if (appt['NAME'] == new_appointment['NAME'] and
            appt_date == new_date and
            appt_time == new_time):
            return "duplicate"

        if appt_date == new_date and appt_time == new_time:
            return "slot_taken"

    appointments.append(new_appointment)

    with open(json_file_path, "w") as f:
        json.dump(appointments, f, indent=2)

    return "success"
