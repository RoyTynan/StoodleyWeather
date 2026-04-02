# API Rules

## Open-Meteo
- Do not change the Open-Meteo API endpoint URL without being explicitly asked.
- Do not add, remove, or rename any weather parameters (e.g. `temperature_2m`, `cloud_cover`) without being explicitly asked.
- The weather parameters are tightly coupled to the UI — changing them will break the display.
- If a task requires adding new weather data, ask the user which parameters to add before making any changes.
- Do not change the API key or customer subdomain without being explicitly asked.

## General API Rules
- Do not introduce new external API calls or third-party services without discussion.
