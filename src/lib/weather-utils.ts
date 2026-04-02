import { HourlyWeatherPoint } from '@/types/types';

export const convertWindSpeedToBeaufort = (windSpeedMs: number): number => {
  if (windSpeedMs >= 34) return 12;
  if (windSpeedMs >= 31) return 11;
  if (windSpeedMs >= 28) return 10;
  if (windSpeedMs >= 25) return 9;
  if (windSpeedMs >= 22) return 8;
  if (windSpeedMs >= 19) return 7;
  if (windSpeedMs >= 16) return 6;
  if (windSpeedMs >= 14) return 5;
  if (windSpeedMs >= 11) return 4;
  if (windSpeedMs >= 8) return 3;
  if (windSpeedMs >= 6) return 2;
  if (windSpeedMs >= 4) return 1;
  return 0;
};

const DIRECTIONS = ["North", "Northeast", "East", "Southeast", "South", "Southwest", "West", "Northwest"];

export function degreesToCompass(degrees: number): string {
  return DIRECTIONS[Math.round(degrees / 45) % 8];
}

export function testagain(a: number, b: number): number {
  return a + b;
}

export function getSummitConditions(hourlyWeatherPoint: HourlyWeatherPoint): { score: number, label: string, colour: string } {
  let score = 100;

  if (hourlyWeatherPoint.windGusts10m! > 50) score -= 30;
  if (hourlyWeatherPoint.windGusts10m! > 35) score -= 20;
  if (hourlyWeatherPoint.visibility! < 200) score -= 25;
  if (hourlyWeatherPoint.visibility! < 1000) score -= 15;
  if (hourlyWeatherPoint.precipitation! > 2) score -= 20;
  if (hourlyWeatherPoint.precipitation! > 0.5) score -= 10;
  if (hourlyWeatherPoint.temperature2m! < 0) score -= 15;

  score = Math.max(0, Math.min(100, score));

  let label: string;
  let colour: string;

  if (score >= 80) {
    label = "Excellent";
    colour = "#22c55e";
  } else if (score >= 60) {
    label = "Good";
    colour = "#84cc16";
  } else if (score >= 40) {
    label = "Fair";
    colour = "#f97316";
  } else {
    label = "Poor";
    colour = "#ef4444";
  }

  return { score, label, colour };
}

export function visibilityToDescription(visibilityMeters: number): string {
  if (visibilityMeters >= 4000) return "Excellent";
  if (visibilityMeters >= 1000) return "Good";
  if (visibilityMeters >= 200) return "Moderate";
  return "Poor";
}

