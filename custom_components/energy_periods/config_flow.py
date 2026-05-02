import voluptuous as vol
from homeassistant import config_entries

DOMAIN = "energy_periods"

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title="Energy Periods",
                data={"sources": [user_input]}
            )

        schema = vol.Schema({
            vol.Required("name"): str,
            vol.Required("source"): str,
            vol.Required("tag"): str,
        })

        return self.async_show_form(step_id="user", data_schema=schema)

class EnergyPeriodsOptionsFlow(config_entries.OptionsFlow):

    def __init__(self, config_entry):
        self.config_entry = config_entry
        self.periods = dict(config_entry.options.get("periods", {}))

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(
            step_id="init",
            menu_options=["workday", "holiday", "save"]
        )

    async def async_step_workday(self, user_input=None):

        if user_input is not None:
            self.periods.setdefault("workday", []).append(user_input)
            return await self.async_step_workday_add_more()

        schema = vol.Schema({
            vol.Required("start"): str,
            vol.Required("end"): str,
            vol.Required("period"): str,
        })

        return self.async_show_form(
            step_id="workday",
            data_schema=schema
        )

    async def async_step_workday_add_more(self, user_input=None):

        if user_input is not None:
            if user_input["more"] == "yes":
                return await self.async_step_workday()
            else:
                return await self.async_step_init()

        return self.async_show_form(
            step_id="workday_add_more",
            data_schema=vol.Schema({
                vol.Required("more", default="no"): vol.In({
                    "yes": "Añadir otro tramo",
                    "no": "Volver"
                })
            })
        )

    async def async_step_holiday(self, user_input=None):

        if user_input is not None:
            self.periods.setdefault("holiday", []).append(user_input)
            return await self.async_step_holiday_add_more()

        schema = vol.Schema({
            vol.Required("start", default="00:00"): str,
            vol.Required("end", default="24:00"): str,
            vol.Required("period", default="valle"): str,
        })

        return self.async_show_form(
            step_id="holiday",
            data_schema=schema
        )

    async def async_step_holiday_add_more(self, user_input=None):

        if user_input is not None:
            if user_input["more"] == "yes":
                return await self.async_step_holiday()
            else:
                return await self.async_step_init()

        return self.async_show_form(
            step_id="holiday_add_more",
            data_schema=vol.Schema({
                vol.Required("more", default="no"): vol.In({
                    "yes": "Añadir otro tramo",
                    "no": "Volver"
                })
            })
        )

    async def async_step_save(self, user_input=None):

        return self.async_create_entry(
            title="Energy Periods",
            data=self.config_entry.data,
            options={
                "periods": self.periods
            }
        )

async def async_get_options_flow(config_entry):
    from .config_flow import EnergyPeriodsOptionsFlow
    return EnergyPeriodsOptionsFlow(config_entry)

