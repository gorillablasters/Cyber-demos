import React from "react";
import styles from "../styles/mission.module.css";

export default function SystemGrid({ children }: { children: React.ReactNode }) {
  return <div className={styles.grid}>{children}</div>;
}
