import pandas as pd
from datetime import datetime, timedelta

file_path = "../data/Sample_Appointment_Data.xlsx"

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

def add_appointment(new_appointment: dict) -> bool:
    df = pd.read_excel(file_path, engine='openpyxl')

    # Convert DATE column to datetime.date objects
    df['DATE'] = pd.to_datetime(df['DATE'], format='%d.%m.%Y').dt.date

    # Convert TIME column to time objects (12-hour format with AM/PM)
    df['TIME'] = pd.to_datetime(df['TIME'], format='%I:%M%p').dt.time

    # Parse new appointment date and time
    new_date = datetime.strptime(new_appointment['DATE'], '%d.%m.%Y').date()
    new_time = datetime.strptime(new_appointment['TIME'], '%I:%M%p').time()

    # Check for duplicate exact match on NAME, DATE, TIME
    is_duplicate = ((df['NAME'] == new_appointment['NAME']) &
                    (df['DATE'] == new_date) &
                    (df['TIME'] == new_time)).any()
    if is_duplicate:
        print("Duplicate appointment found. Not adding.")
        return False

    # Check if the slot (DATE + TIME) is already taken by anyone
    slot_taken = ((df['DATE'] == new_date) & (df['TIME'] == new_time)).any()
    if slot_taken:
        print("Appointment slot not available.")
        return False

    # Append the new appointment row
    df = pd.concat([df, pd.DataFrame([new_appointment])], ignore_index=True)

    # Save back to Excel
    df.to_excel(file_path, index=False, engine='openpyxl')
    print("Appointment added successfully.")
    return True
