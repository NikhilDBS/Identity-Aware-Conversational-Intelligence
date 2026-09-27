// Liquid Metal (metal-fx) — an animated metallic ring effect that wraps any
// element, driven by a single shared WebGL renderer.
//
// Wrap a button, link, or icon with a live metal border:
//   <MetalFx preset="chromatic" strength={1}>
//     <button>Upgrade to Pro</button>
//   </MetalFx>
//
// - preset:  'chromatic' | 'silver' | 'gold'   (each ships dark + light tunings)
// - variant: 'button' (pill ring) | 'circle'   (compact circular ring)
// - theme:   'auto' | 'dark' | 'light'
// - strength (0..1), paused, disableGlow, reflectionTargets, borderRadius, …
//
// All visible instances share one offscreen GL canvas; each composites a
// cropped copy onto its own 2D canvas with a rounded hole punched through.
//
// Source & playground: https://metal.jakubantalik.com
import { MetalFx } from "metal-fx"

export { MetalFx } from "metal-fx"
export type {
  MetalFxProps,
  MetalFxPreset,
  MetalFxVariant,
  MetalFxTheme,
} from "metal-fx"

export default MetalFx
