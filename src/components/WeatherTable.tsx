import { HourlyWeatherPoint } from "../types/types";
import { degreesToCompass } from "../lib/weather-utils";

export type TableView = "rain" | "pressure" | "wind" | "temperature" | "visibility";

const TITLES: Record<TableView, string> = {
  rain: "Hourly Rainfall",
  pressure: "Hourly Surface Pressure",
  wind: "Hourly Wind",
  temperature: "Hourly Temperature",
  visibility: "Hourly Visibility",
};

interface WeatherTableProps {
  view: TableView;
  data: HourlyWeatherPoint[];
}

export default function WeatherTable({ view, data }: WeatherTableProps) {
  return (
    <div className="flex flex-col gap-2">
      <h2 className="text-sm font-semibold text-zinc-600 dark:text-zinc-300 uppercase tracking-wide">
        {TITLES[view]}
      </h2>
      <table className="text-sm border-collapse">
        <thead>
          <tr className="text-left text-zinc-500 dark:text-zinc-400">
            <th className="pr-6 pb-1 font-medium">Hour</th>
            {view === "wind" ? (
              <>
                <th className="pr-6 pb-1 font-medium">Direction</th>
                <th className="pr-6 pb-1 font-medium">Speed (mph)</th>
                <th className="pr-6 pb-1 font-medium">Gusts (mph)</th>
              </>
            ) : (
              <th className="pr-6 pb-1 font-medium">
                {view === "rain" ? "Rain (mm)" : view === "pressure" ? "Pressure (hPa)" : view === "temperature" ? "Temperature (°C / °F)" : "Visibility (m)"}
              </th>
            )}
          </tr>
        </thead>
        <tbody>
          {data.map((point) => (
            <tr key={point.hour} className="border-t border-zinc-100 dark:border-zinc-800">
              <td className="pr-6 py-1 text-zinc-600 dark:text-zinc-300">
                {String(point.hour).padStart(2, "0")}:00
              </td>
              {view === "wind" ? (
                <>
                  <td className="pr-6 py-1 text-zinc-800 dark:text-zinc-100">
                    {point.windDirection10m != null ? degreesToCompass(point.windDirection10m) : "—"}
                  </td>
                  <td className="pr-6 py-1 text-zinc-800 dark:text-zinc-100">{point.windSpeed10m?.toFixed(1) ?? "—"}</td>
                  <td className="pr-6 py-1 text-zinc-800 dark:text-zinc-100">{point.windGusts10m?.toFixed(1) ?? "—"}</td>
                </>
              ) : (
                <td className="pr-6 py-1 text-zinc-800 dark:text-zinc-100">
                  {view === "rain"
                    ? (point.rain?.toFixed(2) ?? "—")
                    : view === "pressure"
                    ? (point.surfacePressure?.toFixed(1) ?? "—")
                    : view === "temperature"
                    ? `${point.temperature2m?.toFixed(1) ?? "—"}°C / ${(point.temperature2m != null ? (point.temperature2m * 9/5 + 32).toFixed(1) : "—")}°F`
                    : (point.visibility ?? "—")}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}