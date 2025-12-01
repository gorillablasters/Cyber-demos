import React, { useEffect, useRef } from "react";

export default function Waterfall() {
  const cRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = cRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d")!;
    let y = 0;

    function draw() {
      const width = canvas.width;
      const row = ctx.createImageData(width, 1);

      for (let i = 0; i < width * 4; i += 4) {
        const val = Math.random() * 255;
        row.data[i] = 0;
        row.data[i + 1] = val;
        row.data[i + 2] = 0;
        row.data[i + 3] = 255;
      }

      ctx.putImageData(row, 0, y);
      y = (y + 1) % canvas.height;

      requestAnimationFrame(draw);
    }

    draw();
  }, []);

  return <canvas width={800} height={300} ref={cRef} />;
}
