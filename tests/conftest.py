"""Test stubs for running unit tests without Home Assistant installed.

The integration code imports Home Assistant modules at import-time.
For these repository-local unit tests, we only need those imports to succeed.
"""

from __future__ import annotations

import sys
import types


def _ensure_module(module_name: str) -> types.ModuleType:
    if module_name in sys.modules:
        return sys.modules[module_name]

    module = types.ModuleType(module_name)
    sys.modules[module_name] = module

    if "." in module_name:
        parent_name, child_name = module_name.rsplit(".", 1)
        parent = _ensure_module(parent_name)
        setattr(parent, child_name, module)

    return module


# Base package
_ensure_module("homeassistant")

# Common subpackages used by the integration
ha_config_entries = _ensure_module("homeassistant.config_entries")
ha_core = _ensure_module("homeassistant.core")
ha_components = _ensure_module("homeassistant.components")
ha_components_sensor = _ensure_module("homeassistant.components.sensor")
ha_data_entry_flow = _ensure_module("homeassistant.data_entry_flow")
ha_exceptions = _ensure_module("homeassistant.exceptions")
ha_helpers = _ensure_module("homeassistant.helpers")
ha_helpers_aiohttp = _ensure_module("homeassistant.helpers.aiohttp_client")
ha_helpers_device_registry = _ensure_module("homeassistant.helpers.device_registry")
ha_helpers_entity_platform = _ensure_module("homeassistant.helpers.entity_platform")
ha_helpers_update_coordinator = _ensure_module("homeassistant.helpers.update_coordinator")
ha_helpers_selector = _ensure_module("homeassistant.helpers.selector")


# Minimal symbols referenced at import-time
class _ConfigEntry:  # noqa: D101
    pass


class _HomeAssistant:  # noqa: D101
    def __init__(self):
        self.data = {}
        self.services = types.SimpleNamespace(
            async_register=lambda *args, **kwargs: None,
            async_remove=lambda *args, **kwargs: None,
        )

        class _ConfigEntries:
            def async_entries(self, domain):  # noqa: ANN001
                return []

        self.config_entries = _ConfigEntries()


class _DataUpdateCoordinator:  # noqa: D101
    def __class_getitem__(cls, item):  # noqa: ANN001
        return cls

    def __init__(self, *args, **kwargs):
        pass


class _CoordinatorEntity:  # noqa: D101
    def __class_getitem__(cls, item):  # noqa: ANN001
        return cls

    def __init__(self, *args, **kwargs):
        pass


class _SensorEntity:  # noqa: D101
    pass


ha_config_entries.ConfigEntry = _ConfigEntry
ha_core.HomeAssistant = _HomeAssistant
ha_core.SupportsResponse = types.SimpleNamespace(ONLY="only")
ha_data_entry_flow.FlowResult = object


class _HomeAssistantError(Exception):
    """Stub for HomeAssistantError."""


ha_exceptions.HomeAssistantError = _HomeAssistantError

ha_helpers_update_coordinator.DataUpdateCoordinator = _DataUpdateCoordinator
ha_helpers_update_coordinator.CoordinatorEntity = _CoordinatorEntity
ha_helpers_update_coordinator.UpdateFailed = Exception

ha_components_sensor.SensorEntity = _SensorEntity
ha_components_sensor.SensorStateClass = types.SimpleNamespace(MEASUREMENT="measurement")

ha_helpers_device_registry.DeviceEntryType = types.SimpleNamespace(SERVICE="service")
ha_helpers_entity_platform.AddEntitiesCallback = object

# Used by config flow; not executed in these tests but safe to stub.
ha_helpers_aiohttp.async_get_clientsession = lambda hass: None

# Selector helpers (optional in the integration)
ha_helpers_selector.selector = lambda x: x
ha_helpers_selector.SelectSelector = object
ha_helpers_selector.SelectSelectorConfig = object
ha_helpers_selector.SelectSelectorMode = object
ha_helpers_selector.SelectOptionDict = dict
