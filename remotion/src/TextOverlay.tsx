import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

const STYLE_COLORS: Record<string, { accent: string; text: string }> = {
  dark: { accent: "#a78bfa", text: "#ffffff" },
  warm: { accent: "#f59e0b", text: "#ffffff" },
  corp: { accent: "#3b82f6", text: "#ffffff" },
  fast: { accent: "#ef4444", text: "#ffffff" },
};

export const TextOverlay: React.FC<{
  title: string; subtitle: string; style: string; duration: number;
}> = ({ title, subtitle, style, duration }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const colors = STYLE_COLORS[style] || STYLE_COLORS.dark;

  // Slide up + fade in
  const progress = spring({ frame, fps, config: { damping: 14, stiffness: 120 } });
  const opacity  = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const fadeOut  = interpolate(frame, [duration * fps - 15, duration * fps], [1, 0], { extrapolateLeft: "clamp" });
  const y        = interpolate(progress, [0, 1], [30, 0]);

  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "flex-start", paddingBottom: 80, paddingLeft: 60 }}>
      {/* Arka plan şeridi */}
      <div style={{
        background:    "linear-gradient(to right, rgba(0,0,0,0.75) 0%, transparent 100%)",
        padding:       "18px 40px 18px 20px",
        borderLeft:    `4px solid ${colors.accent}`,
        opacity:       opacity * fadeOut,
        transform:     `translateY(${y}px)`,
      }}>
        <div style={{
          fontSize: 52, fontWeight: 700, color: colors.text,
          fontFamily: "'Segoe UI', sans-serif", letterSpacing: -1,
          textShadow: "0 2px 8px rgba(0,0,0,0.6)",
        }}>
          {title}
        </div>
        {subtitle && (
          <div style={{
            fontSize: 30, color: colors.accent, marginTop: 6,
            fontFamily: "'Segoe UI', sans-serif", fontWeight: 400,
          }}>
            {subtitle}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
