import aiohttp
from icalendar import Calendar
from datetime import datetime

class ICSProvider:
    def __init__(self, source, tag):
        self.source = source
        self.tag = tag

    async def get_holidays(self):
        if self.source.startswith("http"):
            async with aiohttp.ClientSession() as session:
                async with session.get(self.source) as resp:
                    content = await resp.text()
        else:
            with open(self.source) as f:
                content = f.read()

        cal = Calendar.from_ical(content)
        holidays = {}

        for comp in cal.walk():
            if comp.name != "VEVENT":
                continue

            dt = comp.get("dtstart").dt
            if isinstance(dt, datetime):
                dt = dt.date()

            holidays.setdefault(dt.isoformat(), set()).add(self.tag)

        return holidays
