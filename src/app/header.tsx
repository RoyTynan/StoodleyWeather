export default function Header({ lastFetched }: { lastFetched?: string | null }) {
  return (
    <div className="flex flex-col items-center gap-2 text-center sm:items-start sm:text-left mb-6">
      <h1 className="text-3xl font-semibold leading-10 tracking-tight text-black dark:text-zinc-50">
        Weather Info for Stoodley Pike near Todmorden, West Yorkshire
      </h1>
      {lastFetched && (
        <p className="text-sm text-zinc-500 dark:text-zinc-400">Data fetched: {lastFetched}</p>
      )}
    </div>
  );
}
