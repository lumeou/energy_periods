# Energy Periods (Home Assistant)

Custom integration to define energy tariff periods based on:
- Configurable schedules
- Holidays from multiple sources (ICS)

## Features

- Multiple holiday sources (ICS URL or server file)
- Configurable time periods
- Holiday-aware tariff detection

## Sensors

- sensor.energy_period
- sensor.energy_price
- binary_sensor.weekend
- binary_sensor.holiday
- binary_sensor.non_working_day

## Roadmap

- next_change attribute
- country presets
