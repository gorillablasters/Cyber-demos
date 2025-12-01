export default function SatCard({ sat }: any) {
  return (
    <div className="p-3 border border-green-700 bg-black/40 rounded-md hover:bg-black/60 transition-all">
      <div className="flex justify-between">
        <span className="font-bold">
          [{sat.sat_id.toString(16).toUpperCase().padStart(2, "0")}] {sat.name}
        </span>
        <span className={`${sat.compromised ? "text-red-400" : "text-green-400"}`}>
          {sat.compromised ? "COMPROMISED" : sat.mode}
        </span>
      </div>

      <div className="text-xs mt-1 flex justify-between opacity-80">
        <span>Power: {sat.power_level}%</span>
        <span>Temp: {sat.temp_c.toFixed(1)}°C</span>
      </div>

      {sat.flags && (
        <div className="mt-1 text-xs text-yellow-400">
          {Object.values(sat.flags).map((f: string, i: number) => (
            <div key={i}>{f}</div>
          ))}
        </div>
      )}
    </div>
  );
}
