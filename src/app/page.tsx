"use client";

import { useState } from "react";
import Header from "./header";
import MainContent from "./main-content";

export default function Home() {
  const [lastFetched, setLastFetched] = useState<string | null>(null);
  return (
    <div className="flex min-h-screen bg-zinc-50 font-sans dark:bg-black justify-center">
      <main className="flex flex-col bg-white dark:bg-black p-4 sm:p-8">
        <Header lastFetched={lastFetched} />
        <MainContent onFetch={setLastFetched} />
      </main>
    </div>
  );
}
