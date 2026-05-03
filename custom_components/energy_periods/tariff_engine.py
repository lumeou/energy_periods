from datetime import datetime

def parse_to_seconds(value):
    parts = list(map(int, value.split(":")))

    if len(parts) == 2:
        h, m = parts
        s = 0
    else:
        h, m, s = parts

    return h * 3600 + m * 60 + s

def in_range(current, start, end):
    if start < end:
        # tramo normal
        return start <= current < end
    else:
        # cruza medianoche
        return current >= start or current < end
    
def get_period(now, periods, is_holiday):
    day_type = "non_working_day" if is_holiday else "working_day"

    current = now.hour * 3600 + now.minute * 60 + now.second

    for block in periods.get(day_type, []):
        start = parse_to_seconds(block["start"])
        end = parse_to_seconds(block["end"])

        if in_range(current, start, end):
            return block["type"]

    return None
