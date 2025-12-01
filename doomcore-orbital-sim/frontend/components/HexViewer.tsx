export default function HexViewer({ data }: { data: string }) {
  return (
    <pre style={{ whiteSpace: "pre-wrap", fontSize: "12px" }}>
      {data.match(/.{1,32}/g)?.join("\n") ?? ""}
    </pre>
  );
}
