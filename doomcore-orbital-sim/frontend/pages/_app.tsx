import type { AppProps } from "next/app";
import "../styles/globals.css";
import "../styles/crt.css";

export default function DoomApp({ Component, pageProps }: AppProps) {
  return <Component {...pageProps} />;
}
