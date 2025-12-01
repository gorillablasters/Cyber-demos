export default function LogConsole({ events }: { events: any[] }) {
  return (
    <div style={{ height: "100%", overflowY: "auto", fontSize: "12px" }}>
      {events.map((e, i) => (
        <div key={i}>
          [{new Date(e.ts * 1000).toLocaleTimeString()}] ({e.type})
          — {e.detail}
        </div>
      ))}
    </div>
  );
}
