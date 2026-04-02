const W = 240;
const H = 80;
const PAD = 6;

interface SparkLineProps {
  data: (number | undefined)[];
  label: string;
  unit: string;
  bars?: boolean;
  color?: string;
}

export default function SparkLine({ data, label, unit, bars = false, color = "#6366f1" }: SparkLineProps) {
  const values = data.map((v) => v ?? 0);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const toY = (v: number) => PAD + (1 - (v - min) / range) * (H - PAD * 2);
  const toX = (i: number) => PAD + (i / (values.length - 1)) * (W - PAD * 2);

  const points = values.map((v, i) => `${toX(i)},${toY(v)}`).join(" ");
  const barW = (W - PAD * 2) / values.length - 1;

  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs font-medium text-zinc-500 dark:text-zinc-400">{label} ({unit})</span>
      <svg width={W} height={H} className="bg-zinc-50 dark:bg-zinc-800 rounded">
        {bars ? (
          values.map((v, i) => (
            <rect
              key={i}
              x={PAD + i * (barW + 1)}
              y={toY(v)}
              width={barW}
              height={H - PAD - toY(v)}
              fill={color}
              opacity={0.8}
            />
          ))
        ) : (
          <polyline points={points} fill="none" stroke={color} strokeWidth={1.5} strokeLinejoin="round" />
        )}
        <text x={PAD} y={H - 1} fontSize={9} fill="#a1a1aa">{min.toFixed(1)}</text>
        <text x={W - PAD} y={H - 1} fontSize={9} fill="#a1a1aa" textAnchor="end">{max.toFixed(1)}</text>
      </svg>
    </div>
  );
}
