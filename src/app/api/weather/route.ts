import { NextResponse } from "next/server";
import { getWeatherData } from "../../../api/weather";

export async function GET() {
    const data = await getWeatherData();
    return NextResponse.json(data);
}
