# TODO: No button to add new coin on options, just submit to save which gives an error in logs
# TODO: Capitalize coin name in multiselect
# TODO: Add requirement to have at least one entry in multiselect
"""Error in Sensor
2021-11-16 05:14:48 ERROR (MainThread) [homeassistant.components.sensor] miningpoolhub: Error on device update!
Traceback (most recent call last):
  File "/workspaces/core/homeassistant/helpers/entity_platform.py", line 431, in _async_add_entity
    await entity.async_device_update(warning=False)
  File "/workspaces/core/homeassistant/helpers/entity.py", line 645, in async_device_update
    await task
  File "/workspaces/core/config/custom_components/miningpoolhub/sensor.py", line 170, in async_update
    self.attrs[ATTR_BALANCE_ON_EXCHANGE] = float(
TypeError: float() argument must be a string or a number, not 'NoneType'
"""