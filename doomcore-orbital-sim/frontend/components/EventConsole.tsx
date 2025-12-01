export default function EventConsole({ events }: any) {
  return (
    <div className="flex-1 overflow-y-auto border border-green-700 p-2 rounded bg-black/30">
      {[...events].slice(-120).reverse().map((ev: any, i: number) => (
        <div key={i} className="whitespace-nowrap text-xs">
          {new Date(ev.ts * 1000).toISOString()} ::
          <span className="font-bold"> {ev.type.toUpperCase()} </span>
          sat={ev.sat_id} :: {ev.detail}
        </div>
      ))}
    </div>
  );
}
