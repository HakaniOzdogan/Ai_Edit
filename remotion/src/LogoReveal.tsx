import { AbsoluteFill, Img, interpolate, spring, useCurrentFrame, useVideoConfig, staticFile } from "remotion";

const STYLE_BG: Record<string, string> = {
  dark: "rgba(0,0,0,0.85)",
  warm: "rgba(20,10,5,0.80)",
  corp: "rgba(5,10,20,0.85)",
  fast: "rgba(0,0,0,0.90)",
};

export const LogoReveal: React.FC<{ logoSrc: string; style: string }> = ({ logoSrc, style }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Fade in + scale up ilk 30 frame
  const scale = spring({ frame, fps, config: { damping: 12, stiffness: 80, mass: 0.8 }, from: 0.6, to: 1 });
  const opacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });

  // Fade out son 15 frame
  const fadeOut = interpolate(frame, [durationInFrames - 15, durationInFrames], [1, 0], { extrapolateLeft: "clamp" });
  const finalOpacity = opacity * fadeOut;

  const bg = STYLE_BG[style] || STYLE_BG.dark;

  return (
    <AbsoluteFill style={{ background: bg, justifyContent: "center", alignItems: "center" }}>
      <div style={{ opacity: finalOpacity, transform: `scale(${scale})` }}>
        <Img
          src={logoSrc || staticFile("logo_placeholder.png")}
          style={{ maxWidth: 480, maxHeight: 270, objectFit: "contain" }}
        />
      </div>
    </AbsoluteFill>
  );
};
