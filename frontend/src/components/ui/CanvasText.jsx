import { useRef, useEffect } from "react";

/**
 * CanvasText — renders text inside a coloured pill with a canvas shimmer
 * sweep on top (mix-blend-mode: overlay) that moves left → right infinitely.
 *
 * Props:
 *  text              — string to display
 *  backgroundColor   — CSS colour for the pill background (default deep blue)
 *  colors            — array of CSS colour stops for the shimmer gradient
 *  lineGap           — (unused, kept for API parity)
 *  animationDuration — seconds for one full shimmer cycle (default 6)
 *  className         — extra className on the wrapper span
 */
export function CanvasText({
  text,
  backgroundColor = "#0369a1",
  colors = [
    "rgba(255,255,255,0)",
    "rgba(255,255,255,0.55)",
    "rgba(255,255,255,0)",
  ],
  // eslint-disable-next-line no-unused-vars
  lineGap = 4,
  animationDuration = 6,
  className = "",
}) {
  const wrapRef = useRef(null);
  const canvasRef = useRef(null);
  const rafRef = useRef(null);

  useEffect(() => {
    const wrap = wrapRef.current;
    const canvas = canvasRef.current;
    if (!wrap || !canvas) return;

    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;

    function sync() {
      const { width, height } = wrap.getBoundingClientRect();
      if (!width || !height) return;
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    sync();
    const ro = new ResizeObserver(sync);
    ro.observe(wrap);

    const dur = animationDuration * 1000;
    let t0 = null;

    function frame(ts) {
      if (!t0) t0 = ts;
      const progress = ((ts - t0) % dur) / dur;
      const W = wrap.offsetWidth;
      const H = wrap.offsetHeight;

      ctx.clearRect(0, 0, W, H);

      // Moving shimmer stripe — slightly wider than the element
      const sweepWidth = W * 0.55;
      const x = progress * (W + sweepWidth) - sweepWidth;
      const grad = ctx.createLinearGradient(x, 0, x + sweepWidth, 0);
      const maxI = Math.max(colors.length - 1, 1);
      colors.forEach((c, i) => grad.addColorStop(i / maxI, c));

      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, W, H);

      rafRef.current = requestAnimationFrame(frame);
    }

    rafRef.current = requestAnimationFrame(frame);

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      ro.disconnect();
    };
  }, [colors, animationDuration]);

  return (
    <span
      ref={wrapRef}
      className={`ct-wrap ${className}`}
      style={{ "--ct-bg": backgroundColor }}
    >
      <span className="ct-text">{text}</span>
      <canvas ref={canvasRef} className="ct-canvas" aria-hidden="true" />
    </span>
  );
}
