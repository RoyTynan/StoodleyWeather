/**
 * Unit tests for the getWeatherData() function in weather.ts.
 *
 * These tests verify that the Open-Meteo API response is correctly transformed
 * from columnar format (one array per field) into an array of HourlyWeatherPoint
 * objects (one object per hour), and that HTTP errors are handled correctly.
 *
 * The fetch call is mocked — no real network request is made.
 *
 * To run:
 *   npm test
 *   npm test -- --testPathPattern=weather.test   (this file only)
 */
import { getWeatherData } from './weather';

const mockApiResponse = {
  hourly: {
    time: ['2024-01-15T00:00', '2024-01-15T01:00', '2024-01-15T02:00'],
    temperature_2m: [5.1, 4.8, 4.5],
    snowfall: [0, 0, 0],
    precipitation: [0.1, 0.2, 0],
    rain: [0.1, 0.2, 0],
    cloudcover_low: [20, 30, 25],
    cloudcover_mid: [40, 50, 45],
    cloudcover_high: [60, 70, 65],
    visibility: [10000, 9500, 11000],
    dewpoint_2m: [2.1, 1.8, 1.5],
    precipitation_probability: [10, 20, 5],
    showers: [0, 0, 0],
    weathercode: [1, 2, 1],
    surface_pressure: [1013, 1014, 1015],
    wind_speed_10m: [12.5, 11.0, 10.5],
    wind_direction_10m: [270, 265, 260],
    windgusts_10m: [18.0, 16.5, 15.0],
  },
};

describe('getWeatherData', () => {
  beforeEach(() => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => mockApiResponse,
    });
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  // The API returns arrays of 24 values (one per hour). Each array index
  // maps to the same hour across all fields. Verify the output length matches.
  it('returns one entry per hour', async () => {
    const result = await getWeatherData();
    expect(result).toHaveLength(3);
  });

  // The API uses snake_case columnar arrays (e.g. wind_speed_10m[i]).
  // Verify these are mapped to the correct camelCase fields on each row object.
  it('transforms columnar API response into HourlyWeatherPoint rows', async () => {
    const result = await getWeatherData();
    expect(result[0]).toMatchObject({
      hour: 0,
      time: '2024-01-15T00:00',
      temperature2m: 5.1,
      rain: 0.1,
      surfacePressure: 1013,
      windSpeed10m: 12.5,
      windDirection10m: 270,
      windGusts10m: 18.0,
      visibility: 10000,
    });
  });

  // The `hour` field is derived from the array index, not from the time string.
  // Verify each entry carries the correct index so UI components can use it for ordering.
  it('assigns correct hour index to each entry', async () => {
    const result = await getWeatherData();
    expect(result[0].hour).toBe(0);
    expect(result[1].hour).toBe(1);
    expect(result[2].hour).toBe(2);
  });

  // If the API returns a non-2xx status, getWeatherData() should throw rather
  // than silently returning empty data, so the caller can surface the error.
  // console.error is suppressed here as the error path intentionally logs it.
  it('throws when the API returns a non-ok response', async () => {
    jest.spyOn(console, 'error').mockImplementation(() => {});
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 500 });
    await expect(getWeatherData()).rejects.toThrow('HTTP error! Status: 500');
    jest.restoreAllMocks();
  });
});
