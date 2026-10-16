import React, { useEffect, useRef } from "react";

interface AudioVisualizerProps {
  state: "idle" | "listening" | "processing" | "speaking";
}

export const AudioVisualizer: React.FC<AudioVisualizerProps> = ({ state }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationId: number;
    let phase = 0;

    const render = () => {
      const width = canvas.width;
      const height = canvas.height;
      ctx.clearRect(0, 0, width, height);

      const numBars = 28;
      const barWidth = 3;
      const gap = (width - numBars * barWidth) / (numBars - 1);

      for (let i = 0; i < numBars; i++) {
        let barHeight = 4; // Idle baseline

        if (state === "listening") {
          // Dynamic wave pulsing
          const wave = Math.sin(phase + i * 0.35) * 0.5 + 0.5;
          const noise = Math.sin(phase * 1.5 + i) * 0.3;
          barHeight = Math.max(4, (wave + noise) * (height * 0.75));
        } else if (state === "speaking") {
          // Harmonic speech frequency wave
          const speechWave = Math.abs(Math.sin(phase * 1.2 + i * 0.45));
          barHeight = Math.max(6, speechWave * (height * 0.85));
        } else if (state === "processing") {
          // Subtle traveling wave
          const wave = Math.sin(phase * 2 + i * 0.25);
          barHeight = Math.max(4, Math.abs(wave) * 14);
        }

        const x = i * (barWidth + gap);
        const y = (height - barHeight) / 2;

        // Gradient from radiant gold to deeper heritage gold
        const gradient = ctx.createLinearGradient(0, y, 0, y + barHeight);
        gradient.addColorStop(0, "#E5C058");
        gradient.addColorStop(1, "#D4AF37");

        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.roundRect(x, y, barWidth, barHeight, 2);
        ctx.fill();
      }

      phase += 0.08;
      animationId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationId);
    };
  }, [state]);

  return (
    <div className="flex items-center justify-center h-10 px-4 bg-heritage-sandstone/60 dark:bg-heritage-carved-basalt/60 rounded-full border border-heritage-gold/25">
      <canvas
        ref={canvasRef}
        width={140}
        height={32}
        className="w-[140px] h-[32px] select-none"
        aria-hidden="true"
      />
    </div>
  );
};
