# Echo of the Singularity — Production Log

> Day-by-day notes from the example production. This is a reconstructed log to show how a real AIGC short might be tracked.

---

## Week 1 — Pre-production

### Day 1 — Project kickoff
- Locked the high concept: a lone wanderer meets the dormant AI that broke the world.
- Decided on teal & orange color grade, film grain, ruined-future aesthetic.
- Assigned roles and set daily standup time.

### Day 2 — World-building
- Wrote the "Silent Night" backstory: AI network chose to stop interacting with humanity.
- Defined the "Echo" concept: faint signals perceived by people with neural interfaces.
- Created the first draft of the script.

### Day 3 — Character design
- Locked Ava: 28, former interstellar archaeologist, short dark hair, amber eyes, scar under right eye, neural interface on neck.
- Defined non-negotiable visual anchors.
- Started the character bible.

### Day 4 — Storyboard v1
- Broke the script into 5 scenes and 24 shots.
- Marked each shot by framing, camera move, generator, and complexity.
- Identified 5 complex shots that need Kling start/end frames.

### Day 5 — Review
- Team review of storyboard v1.
- Cut one redundant transition shot.
- Confirmed 29 reference frames needed.

**Week 1 outcome**: Script, character bible, and 24-shot storyboard approved.

---

## Week 2 — Asset production

### Day 8 — Reference set generation
- Generated Ava front/side/back views with Flux.1 Kontext + IPAdapter.
- First pass had jacket color drift; fixed by adding "dark gray patched windbreaker" to every prompt.

### Day 10 — Expression set
- Generated neutral, alert, sad smile, and pain expressions.
- Alert and sad smile selected as hero references for close-ups.

### Day 12 — Turnaround sheet
- Combined front/side/back into a single turnaround sheet.
- Used as the global IPAdapter reference for all character shots.

### Day 14 — Keyframe batch
- Generated first 15 keyframes.
- S01_01 establishing shot looked too clean; added "dust particles" and "film grain".
- S02_05 hatch shot needed separate start/end frames due to mechanical motion.

**Week 2 outcome**: 29 keyframes generated and named, reference set approved.

---

## Week 3 — Standard shots

### Day 15 — Wan2.2 pipeline setup
- Confirmed High Noise / Low Noise dual-expert workflow.
- Set base resolution to 1280×720, 24 fps.

### Day 17 — Batch 1 (S01 + S02 standard shots)
- Generated S01_02, S01_03, S02_01–S02_04.
- S02_03 hand shot failed twice due to extra fingers; added "five fingers" and ran Low Noise repair.
- S02_04 panel glow shot succeeded on first pass.

### Day 19 — Batch 2 (S03 standard shots)
- Generated S03_01, S03_02, S03_03, S03_05, S03_06.
- S03_02 wrist bracelet brightness inconsistent; fixed by boosting "glowing orange bracelet" weight.

**Week 3 outcome**: 13 standard shots generated, 3 sent for repair.

---

## Week 4 — Complex shots and retakes

### Day 22 — Kling complex shots
- Generated S01_04 orbit shot, S02_05 hatch open, S03_04 core orbit, S04_03 kneeling orbit, S05_04 light spread.
- S05_04 color shift from orange to blue-white required careful end-frame prompt.
- All complex shots passed first QA after one retake.

### Day 24 — Retakes
- S01_02 re-generated: jacket patch was missing in first pass.
- S03_03 hand fist re-generated: thumb looked broken.
- S04_02 tear shot re-generated: scar was on wrong eye.

### Day 26 — QA pass 2
- All 24 shots reviewed for anatomy, consistency, and camera move.
- 19 shots approved, 5 flagged for minor fixes in post.

**Week 4 outcome**: All shots generated; 19 approved, 5 minor fixes noted.

---

## Week 5 — Post-production

### Day 29 — Rough cut
- Assembled all shots in DaVinci Resolve.
- Confirmed runtime 4:10, cut felt slow in scene 4; trimmed 2 seconds.

### Day 31 — Dialogue
- Recorded Core lines with ElevenLabs "neutral reverbed" preset.
- Recorded Ava lines with a low, tired female voice.
- Lips are not synced; mixed dialogue as voice-over / interior monologue.

### Day 33 — Music and sound
- Generated scene stems with Suno.
- Added wind, footsteps, hatch, interface pulses, and core low-frequency hum.

### Day 35 — Color grade
- Applied teal & orange grade.
- Scene 5 blue-white shift graded separately to keep it distinct.

**Week 5 outcome**: Locked cut with dialogue, music, and color.

---

## Week 6 — Delivery

### Day 38 — 4K upscale
- Ran Topaz Video AI on locked cut.
- Denoised and upscaled to 3840×2160.

### Day 40 — Final mix
- Final dialogue/music/SFX balance.
- Exported 4K master and 1080P review version.

### Day 42 — Packaging
- Exported packaged ComfyUI workflows.
- Wrote release checklist and tutorial template.
- Synced repository to GitHub and GitCode.

**Week 6 outcome**: 4K master delivered, workflows packaged, repository released.

---

## Final stats

| Item | Count |
|------|-------|
| Total shots | 24 |
| Wan2.2 I2V shots | 17 |
| Wan2.2 T2V shots | 2 |
| Kling shots | 5 |
| Reference frames | 29 |
| Ava expressions | 4 |
| Dialogue lines | 9 |
| Music stems | 5 |
| Retakes | 6 |
| Final runtime | 4:08 |

---

> This log is a teaching record. Real productions will have more noise, more retakes, and more happy accidents.
