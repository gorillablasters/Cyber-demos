import styles from "../styles/mission.module.css";

export default function SatPanel({ sat }: { sat: any }) {
  return (
    <div className={styles.panel}>
      <div className={styles.panelTitle}>{sat.name}</div>

      <div>Mode: {sat.mode}</div>
      <div>Power: {sat.power_level}%</div>
      <div>Temp: {sat.temp_c.toFixed(1)}°C</div>
      <div>Status: {sat.compromised ? "⚠ COMPROMISED" : "OK"}</div>

      {sat.flag_beacon && (
        <div style={{ color: "#ff0066", marginTop: "10px" }}>BEACON ACTIVE</div>
      )}
    </div>
  );
}
