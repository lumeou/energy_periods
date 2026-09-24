# ⚡️ Energy Periods Tariff Engine (Home Assistant)

A robust and highly accurate custom integration designed to calculate real-time energy costs by analyzing complex, multi-layered tariff structures based on time of day, working days, and holidays.

## ✨ Core Capabilities

This engine moves beyond simple period detection; it acts as a full tariff analysis system capable of modeling modern utility rates:

*   **Multi-Tariff Support**: Supports defining and tracking different rate components within a single structure (e.g., **Consumption Rate**, **Peak/Power Rate**, and **Standing Charges**).
*   **Time-Based Periodization**: Determines the current energy period (e.g., Peak, Off-Peak) based on highly configurable schedules for both **Working Days** and **Non-Working Days**.
*   **Cost Calculation Engine**: Calculates crucial financial metrics in real time:
    *   Current Energy Consumption Price (€/kWh).
    *   Daily Power Cost estimate (based on contracted power levels and rates).
    *   Standing Charge monitoring.
*   **Flexible Data Ingestion**: Connects to multiple external holiday sources via the **iCalendar (ICS)** standard, ensuring reliable holiday awareness regardless of the provider's method.
*   **Robust Validation Layer**: Includes a rigorous configuration validation process that ensures all loaded tariff data adheres to strict schemas, preventing runtime errors due to malformed setup.

## 🛰️ Sensors & Entities Provided

The integration exposes comprehensive sensor data for easy monitoring:

* **Energy Consumption**
    * `sensor.energy_consumption_period`: The currently active energy consumption period (e.g., 'Peak', 'Off-Peak').
    * `sensor.energy_consumption_price`: Real-time cost of consumption (€/kWh).
* **Power Term**
    * `sensor.power_term_period`: The currently active power term period.
    * `sensor.power_term_daily_price`: Estimated daily operational power cost.
* **Standing Charges**
    * `sensor.standing_charge_[name]`: Dynamic sensors for each configured standing charge.
* **Calendar & Holidays**
    * `binary_sensor.is_weekend`: True if today is a weekend.
    * `binary_sensor.is_holiday`: Active status flag for public holidays.
    * `binary_sensor.non_working_day`: True if the day is a non-working day (weekend or holiday).

## 🛠️ Technical Details & Architecture

### 🧠 Decision Logic
The `tariff_engine` operates on a hierarchical evaluation process:
* **Day Type Determination**: It first identifies if the current day is a `Working Day` or a `Non-Working Day` (Weekend or Public Holiday fetched via ICS).
* **Temporal Matching**: It scans the corresponding schedule for the identified day type to find the active time block.
* **Fallback Safety**: If no specific block matches, it gracefully reverts to a pre-configured `fallback` period to ensure continuous monitoring.

### 🔄 Data Orchestration
To maintain high performance and stability within Home Assistant:
* **Asynchronous Ingestion**: Holiday data is fetched asynchronously from external iCalendar (ICS) sources.
* **State Management**: Uses the `DataUpdateCoordinator` pattern to centralize data updates, ensuring all sensors stay synchronized and reducing redundant network requests.

### 📋 Configuration Schema
The integration uses a highly flexible, JSON-based schema that supports **date-range-based evolution**. This allows you to plan future tariff changes in advance within a single configuration.

The schema is structured into three main layers:
* **Consumption Layer**: Defines time-based periods (e.g., Peak, Off-Peak) and their corresponding prices (€/kWh).
* **Power Layer**: Manages power term periods, prices, and contracted power levels.
* **Standing Charges**: Allows for additional static or dynamic charges.

For a complete guide, including full JSON structure and practical examples, please refer to [README_TARIFFS.md](./README_TARIFFS.md).

---

### 🚀 Roadmap
* **Enhanced Holiday Management**: 
    * Support for multiple ICS sources via the initial configuration flow.
    * Ability to manage and reconfigure ICS sources through the Options Flow.
* **Advanced Rate Models**: Integration with more complex models (e.g., seasonal adjustments).