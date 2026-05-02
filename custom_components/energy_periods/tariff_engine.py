def get_period(now, config, is_holiday):
    day_type = "non_working_day" if is_holiday else "working_day"
    minutes = now.hour * 60 + now.minute

    for block in config.get(day_type, []):
        sh, sm = map(int, block["start"].split(":"))
        eh, em = map(int, block["end"].split(":"))

        start = sh * 60 + sm
        end = eh * 60 + em

        if start <= minutes < end:
            return block["period"]

    return "unknown"
