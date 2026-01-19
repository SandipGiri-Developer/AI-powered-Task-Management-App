from datetime import datetime, timedelta, timezone

def get_ist_now():
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist)

def format_datetime_ist(dt_str):
    if not dt_str:
        return "No due date"
    try:
        dt = datetime.fromisoformat(dt_str)
        ist = timezone(timedelta(hours=5, minutes=30))
        dt_ist = dt.astimezone(ist)
        return dt_ist.strftime("%d/%m/%Y %H:%M")
    except:
        return dt_str

def to_ist_timestamp(date, time):
    ist = timezone(timedelta(hours=5, minutes=30))
    dt = datetime.combine(date, time)
    dt_ist = ist.localize(dt) if hasattr(ist, 'localize') else dt.replace(tzinfo=ist)
    return dt_ist.isoformat()

def get_hours_until_due(due_date_str):
    if not due_date_str:
        return None
    try:
        due = datetime.fromisoformat(due_date_str)
        now = get_ist_now()
        diff = due - now
        return diff.total_seconds() / 3600
    except:
        return None

def is_within_24h(due_date_str):
    hours = get_hours_until_due(due_date_str)
    return hours is not None and 0 < hours < 24
