"use client";

import { HourlyWeatherPoint } from '@/types/types';
import { getSummitConditions } from '@/lib/weather-utils';

type SummitConditionsProps = {
  data: HourlyWeatherPoint[];
};

export default function SummitConditions({ data }: SummitConditionsProps) {
  return (
    <div>
      <h1>Summit Conditions — Stoodley Pike</h1>
      <div className="flex flex-wrap">
        {data.map((hourlyWeatherPoint, index) => {
          const { label, colour } = getSummitConditions(hourlyWeatherPoint);
          return (
            <div key={index} className={`w-32 h-24 bg-${colour} text-black flex items-center justify-center flex-col`}>
          <p>{hourlyWeatherPoint.time}</p>
          <p>{label}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}