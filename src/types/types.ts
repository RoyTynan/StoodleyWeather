export interface HourlyWeatherPoint {
	hour: number;
	time: string;
	temperature2m?: number;
	snowfall?: number;
	precipitation?: number;
	rain?: number;
	cloudCover?: number;
	cloudCoverLow?: number;
	cloudCoverMid?: number;
	cloudCoverHigh?: number;
	visibility?: number;
	dewPoint2m?: number;
	precipitationProbability?: number;
	showers?: number;
	weatherCode?: number;
	surfacePressure?: number;
	windSpeed10m?: number;
	windDirection10m?: number;
	windGusts10m?: number;
}


export interface HourlyWeatherPointTest {
	hour: number;
	time: string;
	temperature2m?: number;
	snowfall?: number;
	precipitation?: number;
	rain?: number;
	cloudCover?: number;
	cloudCoverLow?: number;
	cloudCoverMid?: number;
	cloudCoverHigh?: number;
	visibility?: number;
	dewPoint2m?: number;
	precipitationProbability?: number;
	showers?: number;
	weatherCode?: number;
	surfacePressure?: number;
	windSpeed10m?: number;
	windDirection10m?: number;
	windGusts10m?: number;
}
