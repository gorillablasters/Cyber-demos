export default function TelemetryPanel({ sat }: { sat: any }) {
  return (
    <div style={{ fontSize: "12px" }}>
      <div>Seq: {sat.sequence_counter}</div>
      <div>Last Contact: {new Date(sat.last_contact_unix * 1000).toLocaleString()}</div>
      <div>RF Neighbors: {Array.from(sat.rf_neighbors).join(", ")}</div>
      <div>Crosslink Key: {sat.crosslink_key ? "(loaded)" : "(none)"}</div>
    </div>
  );
}
