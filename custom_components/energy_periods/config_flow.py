import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

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

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EnergyPeriodsOptionsFlow(config_entry)


class EnergyPeriodsOptionsFlow(config_entries.OptionsFlow):

    def __init__(self, config_entry):
        self.config_entry = config_entry

        # estado persistente del editor
        self.periods = dict(config_entry.options.get("periods", {}))
        self._current_day_type = None

    # ----------------------------------------------------
    # MENÚ PRINCIPAL
    # ----------------------------------------------------

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(
            step_id="init",
            menu_options={
                "working_day": "Working day",
                "non_working_day": "Non-working day",
                "save": "Save"
            }
        )

    # ----------------------------------------------------
    # ENTRADA WORKING DAY
    # ----------------------------------------------------

    async def async_step_working_day(self, user_input=None):
        self._current_day_type = "working_day"
        return await self._render_list()

    # ----------------------------------------------------
    # ENTRADA NON WORKING DAY
    # ----------------------------------------------------

    async def async_step_non_working_day(self, user_input=None):
        self._current_day_type = "non_working_day"
        return await self._render_list()

    # ----------------------------------------------------
    # LISTA DE TRAMOS (VIEW PRINCIPAL DEL EDITOR)
    # ----------------------------------------------------

    async def _render_list(self):

        day_type = self._current_day_type
        periods = self.periods.setdefault(day_type, [])

        menu = {}

        # cada tramo abre un STEP de edición o borrado
        for i, p in enumerate(periods):
            menu[f"edit_{i}"] = f"✏️ {p['start']} → {p['end']} ({p['type']})"
            menu[f"delete_{i}"] = f"🗑 {p['start']} → {p['end']} ({p['type']})"

        # acciones globales
        menu["add"] = "➕ Add period"
        menu["back"] = "⬅ Back"
        menu["save"] = "💾 Save"

        return self.async_show_menu(
            step_id="period_list",
            menu_options=menu
        )

    # ----------------------------------------------------
    # DISPATCH LISTA (ÚNICO PUNTO DE CONTROL)
    # ----------------------------------------------------

    async def async_step_period_list(self, user_input=None):

        if not user_input:
            return await self._render_list()

        action = next(iter(user_input))
        periods = self.periods[self._current_day_type]

        # -------------------------
        # BACK
        # -------------------------
        if action == "back":
            return await self.async_step_init()

        # -------------------------
        # SAVE
        # -------------------------
        if action == "save":
            return await self.async_step_save()

        # -------------------------
        # ADD
        # -------------------------
        if action == "add":
            return await self.async_step_add_period()

        # -------------------------
        # EDIT
        # -------------------------
        if action.startswith("edit_"):
            idx = int(action.split("_")[1])
            return await self.async_step_edit_period(idx)

        # -------------------------
        # DELETE
        # -------------------------
        if action.startswith("delete_"):
            idx = int(action.split("_")[1])

            if 0 <= idx < len(periods):
                periods.pop(idx)

            return await self._render_list()

        return await self._render_list()

    # ----------------------------------------------------
    # ADD PERIOD
    # ----------------------------------------------------

    async def async_step_add_period(self, user_input=None):

        if user_input is not None:
            self.periods.setdefault(self._current_day_type, []).append(user_input)
            return await self._render_list()

        schema = vol.Schema({
            vol.Required("start"): selector.TimeSelector(),
            vol.Required("end"): selector.TimeSelector(),
            vol.Required("type"): selector.TextSelector(),
        })

        return self.async_show_form(
            step_id="add_period",
            data_schema=schema
        )

    # ----------------------------------------------------
    # EDIT PERIOD (reutiliza form)
    # ----------------------------------------------------

    async def async_step_edit_period(self, idx, user_input=None):

        periods = self.periods[self._current_day_type]

        if idx >= len(periods):
            return await self._render_list()

        if user_input is not None:
            periods[idx] = user_input
            return await self._render_list()

        p = periods[idx]

        schema = vol.Schema({
            vol.Required("start", default=p["start"]): selector.TimeSelector(),
            vol.Required("end", default=p["end"]): selector.TimeSelector(),
            vol.Required("type", default=p["type"]): selector.TextSelector(),
        })

        return self.async_show_form(
            step_id="edit_period",
            data_schema=schema
        )

    # ----------------------------------------------------
    # SAVE FINAL
    # ----------------------------------------------------

    async def async_step_save(self, user_input=None):

        return self.async_create_entry(
            title="Energy Periods",
            data=self.config_entry.data,
            options={
                "periods": self.periods
            }
        )
  
