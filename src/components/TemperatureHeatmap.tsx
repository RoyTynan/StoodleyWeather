"use client";

import { HourlyWeatherPoint } from "@/types/types";

const TemperatureHeatmap = ({ data }: { data: HourlyWeatherPoint[] }) => {
const minTemp = Math.min(...data.map((point) => point.temperature2m ?? 0));
const maxTemp = Math.max(...data.map((point) => point.temperature2m ?? 0));

  const getCellColor = (temperature: number) => {
    const blue = 0x3b82f6;
    const red = 0xef4444;
    const t = (temperature - minTemp) / (maxTemp - minTemp);
const r = Math.round((1 - t) * (blue >> 16) + t * (red >> 16));
const g = Math.round((1 - t) * ((blue >> 8) & 0xff) + t * ((red >> 8) & 0xff));
const b = Math.round((1 - t) * (blue & 0xff) + t * (red & 0xff));
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
  };

  return (
    <div className="flex flex-wrap">
      {data.map((point, index) => (
<div key={index} className="w-20 h-16 flex items-center justify-center text-white" style={{ backgroundColor: getCellColor(point.temperature2m ?? 0) }}>
  {`${String(index).padStart(2, '0')}:00 ${(point.temperature2m ?? 0).toFixed(1)}°C`}
</div>
      ))}
    </div>
  );
};

export default TemperatureHeatmap;