import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

export const TransitionComp: React.FC<{ type: string; style: string }> = ({ type, style }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const mid = durationInFrames / 2;

  // Flash efekti
  if (type === "flash") {
    const opacity = frame < mid
      ? interpolate(frame, [0, mid], [0, 1], { extrapolateRight: "clamp" })
      : interpolate(frame, [mid, durationInFrames], [1, 0], { extrapolateLeft: "clamp" });
    return (
      <AbsoluteFill style={{ background: "white", opacity }} />
    );
  }

  // Glitch efekti
  if (type === "glitch") {
    const shake = frame % 3 === 0 ? (Math.random() - 0.5) * 10 : 0;
    const opacity = interpolate(frame, [0, mid, durationInFrames], [0, 1, 0]);
    return (
      <AbsoluteFill style={{
        background: style === "fast" ? "#ef4444" : "#a78bfa",
        opacity,
        transform: `translate(${shake}px, ${shake * 0.5}px)`,
        mixBlendMode: "screen",
      }} />
    );
  }

  // Varsayılan: fade
  const opacity = interpolate(frame, [0, mid, durationInFrames], [0, 0.8, 0]);
  return <AbsoluteFill style={{ background: "black", opacity }} />;
};
