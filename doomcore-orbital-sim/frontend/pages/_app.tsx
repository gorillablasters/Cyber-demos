import { useEffect } from "react";
import { syncSidWithServer } from "../lib/api";
import type { AppProps } from "next/app";
import "../styles/globals.css";
import "../styles/crt.css";


export default function DoomApp({ Component, pageProps }: AppProps) {
  useEffect(() => {
    syncSidWithServer();
  }, []);

  return <Component {...pageProps} />;
}
