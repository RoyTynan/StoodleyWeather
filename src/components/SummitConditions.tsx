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
      <div className="flex flex-col">
        {data.map((hourlyWeatherPoint, index) => {
          const { label, colour } = getSummitConditions(hourlyWeatherPoint);
          const timeString = new Date(hourlyWeatherPoint.time).toLocaleTimeString([], { hour: '2-digit', hour12: true }).replace(/^0/, '').toLowerCase();
          return (
            <div key={index} className={`w-32 h-24 bg-${colour} text-black flex items-center justify-center flex-col`}>
              <p>
                {timeString === '12 am' ? 'Midnight' : timeString === '12 pm' ? 'Noon' : timeString}
              </p>
              <p>{label}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}