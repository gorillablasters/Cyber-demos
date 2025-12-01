import Link from "next/link";
import styles from "../styles/header.module.css";

export default function DoomHeader() {
  return (
    <header className={styles.header}>
      <div className={styles.title}>MF DOOM — ORBITAL OPS CONSOLE</div>

      <nav className={styles.nav}>
        <Link href="/">Dashboard</Link>
        <Link href="/telemetry">Telemetry</Link>
        <Link href="/rf">RF</Link>
        <Link href="/crosslink">Crosslink</Link>
        <Link href="/firmware">Firmware</Link>
        <Link href="/hex">Hex</Link>
      </nav>
    </header>
  );
}
