"use client";

import { useState, useRef } from "react";
import { HourlyWeatherPoint } from "../types/types";
import { saveWeatherData, loadWeatherData } from "../lib/weather-db";
import WeatherTable, { TableView } from "../components/WeatherTable";
import SummitConditions from "@/components/SummitConditions";
import TemperatureHeatmap from "@/components/TemperatureHeatmap";
import SparkLine from "../components/SparkLine";

const COOLDOWN_MS = 5 * 60 * 1000;

type ViewType = TableView | "chart" | "heatmap" | "summit";

export default function MainContent({ onFetch }: { onFetch?: (timestamp: string) => void }) {
  const [loading, setLoading] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [weatherData, setWeatherData] = useState<HourlyWeatherPoint[] | null>(null);
  const [view, setView] = useState<ViewType | null>(null);
  const [status, setStatus] = useState("");
  const cooldownTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchWeather = async () => {
    if (loading || cooldown > 0) return;
    setLoading(true);
    try {
      const res = await fetch("/api/weather");
      if (!res.ok) throw new Error(`HTTP error: ${res.status}`);
      const hourlyData: HourlyWeatherPoint[] = await res.json();
      await saveWeatherData(hourlyData);
      onFetch?.(new Date().toLocaleString('en-GB', { dateStyle: 'long', timeStyle: 'short' }));
    } catch (error) {
      console.error("Error fetching weather data:", error);
    } finally {
      setLoading(false);
      startCooldown();
    }
  };

  const loadAndShow = async (v: ViewType) => {
    try {
      const data = await loadWeatherData();
      if (!data) {
        setStatus("No weather data in storage. Fetch it first.");
        setWeatherData(null);
        setView(null);
      } else {
        setStatus("");
        setWeatherData(data);
        setView(v);
      }
    } catch (error) {
      setStatus("Error reading from IndexedDB.");
      console.error(error);
    }
  };

  const startCooldown = () => {
    let remaining = COOLDOWN_MS / 1000;
    setCooldown(remaining);
    cooldownTimer.current = setInterval(() => {
      remaining -= 1;
      if (remaining <= 0) {
        clearInterval(cooldownTimer.current!);
        setCooldown(0);
      } else {
        setCooldown(remaining);
      }
    }, 1000);
  };

  const fetchLabel = loading ? "Fetching..." : cooldown > 0 ? `Wait ${cooldown}s` : "Get Weather Data";
  const btnClass = "px-4 py-2 bg-zinc-200 dark:bg-zinc-700 rounded hover:bg-zinc-300 dark:hover:bg-zinc-600 font-medium";

  return (
    <div className="flex flex-row gap-8 text-base font-medium">

      {/* Left — controls */}
      <div className="flex flex-col gap-4 w-48 shrink-0">
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          Fetches current hourly weather data for Stoodley Pike. Limited to once every 5 minutes to avoid API rate restrictions.
        </p>
        <button onClick={fetchWeather} disabled={loading || cooldown > 0}
          className={`${btnClass} disabled:opacity-50 disabled:cursor-not-allowed`}>
          {fetchLabel}
        </button>
        <button onClick={() => loadAndShow("rain")} className={btnClass}>Show Rain</button>
        <button onClick={() => loadAndShow("pressure")} className={btnClass}>Show Surface Pressure</button>
        <button onClick={() => loadAndShow("wind")} className={btnClass}>Show Wind</button>
        <button onClick={() => loadAndShow("visibility")} className={btnClass}>Show Visibility</button>
<button onClick={() => loadAndShow("temperature")} className={btnClass}>Show Temperature</button>
        <button onClick={() => loadAndShow("heatmap")} className={btnClass}>Show Heatmap</button>
<button onClick={() => loadAndShow("summit")} className={btnClass}>Show Summit Conditions</button>
        <button onClick={() => loadAndShow("chart")} className={btnClass}>Show Charts</button>
        {status && <p className="text-sm text-red-500">{status}</p>}
      </div>

      {/* Right — table or charts */}
      {weatherData && view && view !== "chart" && view !== "heatmap" && view !== "summit" && (
        <WeatherTable view={view} data={weatherData} />
      )}

{weatherData && view === "heatmap" && (
    <TemperatureHeatmap data={weatherData} />
)}

{weatherData && view === "summit" && (
  <SummitConditions data={weatherData} />
)}

{weatherData && view === "chart" && (
        <div className="grid grid-cols-2 gap-6">
          <SparkLine label="Temperature" unit="°C" data={weatherData.map((p) => p.temperature2m)} color="#f97316" />
          <SparkLine label="Rain" unit="mm" data={weatherData.map((p) => p.rain)} color="#3b82f6" bars />
          <SparkLine label="Wind Speed" unit="mph" data={weatherData.map((p) => p.windSpeed10m)} color="#8b5cf6" />
          <SparkLine label="Wind Gusts" unit="mph" data={weatherData.map((p) => p.windGusts10m)} color="#a78bfa" />
          <SparkLine label="Surface Pressure" unit="hPa" data={weatherData.map((p) => p.surfacePressure)} color="#10b981" />
          <SparkLine label="Visibility" unit="m" data={weatherData.map((p) => p.visibility)} color="#06b6d4" />
          <SparkLine label="Precipitation Probability" unit="%" data={weatherData.map((p) => p.precipitationProbability)} color="#3b82f6" />
          <SparkLine label="Cloud Cover Low" unit="%" data={weatherData.map((p) => p.cloudCoverLow)} color="#94a3b8" />
        </div>
      )}

    </div>
  );
}
