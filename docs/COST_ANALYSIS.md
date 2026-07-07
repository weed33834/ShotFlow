# ShotFlow — Cost Reference

English (current) | [中文](./COST_ANALYSIS.zh.md)

> This document estimates the costs of two approaches for producing a 3–5 minute AIGC short film using this project: a local GPU approach and a cloud API approach. Actual costs vary depending on model versions, number of generations, and number of reruns.

---

## Option 1: Local GPU Approach

Suitable for teams that have an RTX 4090 or equivalent GPU and want full control over the generation process.

| Item | Estimated Cost | Notes |
|------|----------|------|
| RTX 4090 24GB | Already purchased ~0 yuan / rental ~300–600 yuan/month | 0 cost if you already own the hardware |
| Electricity | ~50–100 yuan/film | Estimated based on 100 hours at full load |
| Model download | 0 yuan | Open-source models |
| Kling API (complex shots) | ~50–100 yuan | 5 complex shots, estimated at 0.5–1 yuan/5s |
| ElevenLabs voiceover | ~0–50 yuan | Free quota is usually sufficient |
| Suno music | ~0–100 yuan | Free quota can generate multiple tracks |
| DaVinci/Topaz | 0 yuan/subscription fee | DaVinci free version is sufficient; Topaz subscription as needed |
| **Total** | **~100–900 yuan/film** | Mainly depends on whether a local GPU is available |

---

## Option 2: Cloud API Approach

Suitable for teams without a local GPU that want to produce content quickly.

| Item | Estimated Cost | Notes |
|------|----------|------|
| Keyframe generation (Flux API) | ~30–60 yuan | 29 keyframes, ~60–120 after reruns |
| Standard shot video (Kling/Runway) | ~300–800 yuan | 19 standard shots, each 3–5s |
| Complex shot video (Kling first-last frame) | ~50–150 yuan | 5 complex shots |
| ElevenLabs voiceover | ~0–50 yuan | |
| Suno music | ~0–100 yuan | |
| DaVinci/Topaz | 0 yuan/subscription fee | |
| **Total** | **~400–1200 yuan/film** | Depends on API choice and number of reruns |

---

## Money-Saving Tips

1. **Run keyframes with local Flux first**, and only use the cloud for video generation;
2. **Prioritize Wan2.2 local generation for standard shots**, and only call Kling for complex/transition shots;
3. **Use the free quota for voiceover and music first**, and pay only when insufficient;
4. **Set up a render queue** to avoid duplicate generation;
5. **Use `video_quality_check.py` to filter out broken shots early**, reducing wasted reruns.

---

## Time Cost

| Stage | Estimated Time |
|------|----------|
| Planning and storyboarding | 3–5 days |
| Character consistency verification | 2–3 days |
| Keyframe generation | 1–2 days |
| Video generation | 3–5 days |
| Post-production compositing | 3–5 days |
| **Total** | **~2–3 weeks** |

---

> The above estimates are for reference only; actual costs are subject to real-time pricing on each platform.
