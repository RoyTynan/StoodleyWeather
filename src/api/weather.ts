import { HourlyWeatherPoint } from '../types/types';
import { STOODLEY_LAT, STOODLEY_LON } from '../lib/constants';

export async function getWeatherData(): Promise<HourlyWeatherPoint[]> {
  try {
    const today = new Date().toISOString().split('T')[0];
    const params = new URLSearchParams({
      latitude: String(STOODLEY_LAT),
      longitude: String(STOODLEY_LON),
      start_date: today,
      end_date: today,
      hourly: 'temperature_2m,snowfall,precipitation,rain,cloudcover_low,cloudcover_mid,cloudcover_high,visibility,dewpoint_2m,precipitation_probability,showers,weathercode,surface_pressure,wind_speed_10m,wind_direction_10m,windgusts_10m',
      timezone: 'Europe/London',
      wind_speed_unit: 'mph',
      precipitation_unit: 'mm',
      models: 'best_match',
    });
    const response = await fetch(`https://api.open-meteo.com/v1/forecast?${params}`);
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    const data = await response.json();
    const h = data.hourly;
    return h.time.map((time: string, i: number): HourlyWeatherPoint => ({
      hour: i,
      time,
      temperature2m:            h.temperature_2m?.[i],
      snowfall:                  h.snowfall?.[i],
      precipitation:             h.precipitation?.[i],
      rain:                      h.rain?.[i],
      cloudCoverLow:             h.cloudcover_low?.[i],
      cloudCoverMid:             h.cloudcover_mid?.[i],
      cloudCoverHigh:            h.cloudcover_high?.[i],
      visibility:                h.visibility?.[i],
      dewPoint2m:                h.dewpoint_2m?.[i],
      precipitationProbability:  h.precipitation_probability?.[i],
      showers:                   h.showers?.[i],
      weatherCode:               h.weathercode?.[i],
      surfacePressure:           h.surface_pressure?.[i],
      windSpeed10m:              h.wind_speed_10m?.[i],
      windDirection10m:          h.wind_direction_10m?.[i],
      windGusts10m:              h.windgusts_10m?.[i],
    }));
  } catch (error) {
    console.error('Error fetching weather data:', error);
    throw error;
  }
}
