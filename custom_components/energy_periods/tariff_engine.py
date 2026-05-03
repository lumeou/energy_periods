from datetime import datetime

def parse_time(value):
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    raise ValueError(f"Invalid time format: {value}")

def get_period(now, config, is_holiday):
    day_type = "non_working_day" if is_holiday else "working_day"
    minutes = now.hour * 60 + now.minute

    for block in config.get(day_type, []):
        start_t = parse_time(block["start"])
        end_t = parse_time(block["end"])

        start = start_t.hour * 60 + start_t.minute
        end = end_t.hour * 60 + end_t.minute

        if start <= minutes < end:
            return block["type"]

    return None
