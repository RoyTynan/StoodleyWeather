"use client";

import { useEffect, useRef } from "react";

declare global {
  interface Window {
    Cesium: any;
  }
}

interface CompassProps {
  heading: number; // in radians
}

export default function Compass({ heading }: CompassProps) {
  const compassRef = useRef<HTMLDivElement>(null);

  // Convert heading (radians) to degrees for CSS rotation
  // Cesium heading: 0 = North, positive = clockwise
  const headingDegrees = (heading * 180) / Math.PI;

  useEffect(() => {
    if (compassRef.current) {
      // Rotate the compass needle
      compassRef.current.style.transform = `rotate(${headingDegrees}deg)`;
    }
  }, [headingDegrees]);

  return (
    <div className="absolute top-4 right-7 -ml-5 z-10">
      {/* Compass outer ring */}
      <div className="relative w-24 h-24">
        <div className="absolute inset-0 rounded-full border-4 border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 shadow-lg flex items-center justify-center">
          {/* North indicator */}
          <div className="absolute top-2 text-zinc-800 dark:text-zinc-200 font-bold text-sm">N</div>
          {/* East indicator */}
          <div className="absolute right-2 text-zinc-600 dark:text-zinc-400 text-xs">E</div>
          {/* South indicator */}
          <div className="absolute bottom-2 text-zinc-800 dark:text-zinc-200 font-bold text-sm">S</div>
          {/* West indicator */}
          <div className="absolute left-2 text-zinc-600 dark:text-zinc-400 text-xs">W</div>

          {/* Compass needle */}
          <div
            ref={compassRef}
            className="absolute inset-0 flex items-center justify-center transition-transform duration-100 ease-out"
          >
            {/* Needle container */}
            <div className="relative w-16 h-16">
              {/* North point (red) */}
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-0 h-0 border-l-[8px] border-l-transparent border-r-[8px] border-r-transparent border-b-[32px] border-b-red-500 drop-shadow-md" />
              {/* South point (white) */}
              <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-0 h-0 border-l-[8px] border-l-transparent border-r-[8px] border-r-transparent border-t-[32px] border-t-white drop-shadow-md" />
            </div>
          </div>

          {/* Center dot */}
          <div className="absolute w-3 h-3 bg-zinc-400 dark:bg-zinc-600 rounded-full" />
        </div>

        {/* Compass label */}
        <div className="absolute -bottom-6 left-1/2 -translate-x-1/2 text-sm text-white uppercase tracking-wide whitespace-nowrap">
          Looking towards
        </div>
      </div>
    </div>
  );
}
