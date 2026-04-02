import { HourlyWeatherPoint } from "../types/types";

const DB_NAME = "stoodleyweather";
const DB_VERSION = 1;
const STORE_NAME = "weatherData";

type HourlyRecord = Record<string, HourlyWeatherPoint>;

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => { request.result.createObjectStore(STORE_NAME); };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

function formatByHour(data: HourlyWeatherPoint[]): HourlyRecord {
  return Object.fromEntries(data.map((p) => [String(p.hour).padStart(2, "0"), p]));
}

export async function saveWeatherData(data: HourlyWeatherPoint[]): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).put({ hours: formatByHour(data), savedAt: new Date().toISOString() }, "current");
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function loadWeatherData(): Promise<HourlyWeatherPoint[] | null> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const request = tx.objectStore(STORE_NAME).get("current");
    request.onsuccess = () => {
      const result = request.result;
      if (!result?.hours) { resolve(null); return; }
      const hours: HourlyRecord = result.hours;
      resolve(Object.keys(hours).sort().map((k) => hours[k]));
    };
    request.onerror = () => reject(request.error);
  });
}
