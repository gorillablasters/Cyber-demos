import React, { useRef, useEffect } from "react";

export default function CrosslinkMap({ sats }: { sats: any[] }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const ctx = ref.current?.getContext("2d");
    if (!ctx) return;

    function draw() {
      ctx.clearRect(0, 0, 800, 300);

      sats.forEach((s: any, i: number) => {
        const x = 150 + i * 150;
        const y = 150;

        ctx.beginPath();
        ctx.arc(x, y, 40, 0, Math.PI * 2);
        ctx.strokeStyle = s.compromised ? "#ff0044" : "#00ff66";
        ctx.lineWidth = 3;
        ctx.stroke();

        ctx.fillStyle = "#00ff66";
        ctx.fillText(s.name, x - 30, y + 60);
      });

      requestAnimationFrame(draw);
    }

    draw();
  }, [sats]);

  return <canvas width={800} height={300} ref={ref} />;
}
