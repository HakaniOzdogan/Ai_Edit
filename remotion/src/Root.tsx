import { Composition } from "remotion";
import { LogoReveal }   from "./LogoReveal";
import { TextOverlay }  from "./TextOverlay";
import { TransitionComp } from "./Transition";

export const RemotionRoot = () => (
  <>
    <Composition id="LogoReveal"   component={LogoReveal}   durationInFrames={75}  fps={25} width={1920} height={1080} defaultProps={{ logoSrc:"", style:"dark" }} />
    <Composition id="TextOverlay"  component={TextOverlay}  durationInFrames={125} fps={25} width={1920} height={1080} defaultProps={{ title:"", subtitle:"", style:"dark", duration:5 }} />
    <Composition id="Transition"   component={TransitionComp} durationInFrames={25} fps={25} width={1920} height={1080} defaultProps={{ type:"fade", style:"dark" }} />
  </>
);
