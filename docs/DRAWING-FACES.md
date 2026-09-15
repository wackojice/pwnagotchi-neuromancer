# Drawing your own faces

Three principles, learned the hard way:

- **Solid fills, not thin strokes.** A 1 px outline vanishes or shimmers on
  e-ink; a black mass always survives.
- **No vector primitives.** A mouth drawn as an arc, or text set in a font,
  clashes with pixel art. Draw by hand, at final size.
- **No writing inside the visor.** It is about 50 px wide once scaled down, so
  a word set there survives as three or four grey dots and nothing more. Two
  labels were drawn and thrown away before this sank in. Put the words in the
  voice instead, where they render large next to the face — `NULL SIGNAL.`
  started life inside the visor and reads far better as a line.

There are two patterns to reuse, matching the two axes described in
[The faces](../README.md#the-faces).
**Machine state**: the visor as a solid black block with the motif knocked out
in white — `sleep.png`, `bored.png` and the `upload` set all work this way, and
the block is what makes them readable across a room. **Mood**: leave the visor
lit and redraw the mouth only, as `happy.png` and `angry.png` do. Changing both
at once usually makes it look like a different character — `sad.png` is the
one exception, and deliberately so: it is boredom gone on, so the flat trace
stays *and* the mouth falls *and* a broken heart appears. Three signs piling
up, because the situation got worse.

Two more things, learned by throwing drawings away:

- **Draw at an exact multiple of the target.** 1216 × 1280 is 16× a 76 × 80
  face, so every 16 × 16 block becomes one pixel with nothing to interpolate.
  Off-multiples introduce noise in areas you never touched.
- **Never redraw the outline.** The drawings that failed were the ones where
  the silhouette shifted — a face 4 px lower, lenses a different shape. In
  isolation they looked fine; alternating with the original, the head jumps.

---

[Back to the README](../README.md)
