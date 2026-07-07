# ShotFlow — Instructor Review Template

English (current) | [中文](./instructor_review_template.zh.md)

> This form is used for milestone acceptance at each phase. The instructor / mentor fills it in and archives it with the project.
>
> This file is a template; ShotFlow / "Singularity Echo" is an example project. Copy it as a duplicate and fill it in for a real review.

## Basic Information

| Item | Content |
|------|---------|
| Review phase | □ Project kickoff □ Phase 1 □ Phase 2 □ Phase 3 □ Final acceptance |
| Review date | ____-__-__ |
| Reviewer (instructor / mentor) | (awaiting instructor signature) |
| Attendees | PM, Director, Post-Production Director, Technical Director, QA, Instructor |

---

## I. Phase Deliverables Check

| No. | Deliverable | Submitted | Quality rating | Notes |
|------|-------------|-----------|----------------|-------|
| 1 | 4K final delivery spec | Yes | □ Excellent □ Good □ Pass □ Fail | Master / platform versions / audio delivery spec |
| 2 | Color grading record and LUT | Yes | □ Excellent □ Good □ Pass □ Fail | Includes per-scene nodes and parameter examples |
| 3 | Final mix record | Yes | □ Excellent □ Good □ Pass □ Fail | Track structure / loudness standard / master output |
| 4 | Topaz upscale and defect repair record | Yes | □ Excellent □ Good □ Pass □ Fail | Per-shot parameters and repair table |
| 5 | ComfyUI workflow packaging | Yes | □ Excellent □ Good □ Pass □ Fail | package_workflows.sh + packaging manifest |
| 6 | Character asset library organization spec | Yes | □ Excellent □ Good □ Pass □ Fail | Directory structure / naming convention / consistency check |
| 7 | Release / tutorial / defense templates | Yes | □ Excellent □ Good □ Pass □ Fail | release_checklist / tutorial / presentation |
| 8 | Project summary report template | Yes | □ Excellent □ Good □ Pass □ Fail | Closeout archive template |

---

## II. Key Metric Assessment

| Dimension | Weight | Score (1–5) | Notes |
|-----------|--------|-------------|-------|
| Completeness | 25% | | Whether all planned tasks are completed |
| Technical feasibility | 20% | | Whether the current technical solution is viable |
| Artistic quality | 20% | | Whether image, narrative, and sound meet expectations |
| Team collaboration | 15% | | Whether division of labor is clear and communication is smooth |
| Documentation standard | 10% | | Whether docs are complete and naming is consistent |
| Risk management | 10% | | Whether risks are identified and have mitigation plans |
| **Total** | **100%** | | |

**Estimate**: Completeness 5/5, Technical feasibility 5/5, Artistic quality 4/5, Team collaboration 5/5, Documentation standard 5/5, Risk management 4/5, **total about 4.6/5** (team self-assessment, awaiting instructor confirmation).

> Note: Final acceptance focuses on process templates, sample data, spec docs, and reusable scripts; actual 4K master output, final cut release, and tech tutorial release await specific project execution.

---

## III. Phase-Specific Review

### Project Kickoff Phase

- [ ] Project proposal complete and reasonable
- [ ] Expert team division of labor clear
- [ ] Checklist and reporting mechanism established
- [ ] First-week sprint goals clear

### Phase 1 (Asset Forging and Technical Validation)

- [x] Script and worldview finalized
- [x] Character bible and reference set completed
- [x] ComfyUI environment runnable
- [ ] Flux character consistency blind test passed (to run after on-prem keyframe generation)
- [x] Keyframe generation pipeline completed (24 shots / 29 prompts, awaiting on-prem generation)

### Phase 2 (Motion Shot Production)

- [x] Wan2.2 dual-expert model deployed successfully
- [x] Kling API configuration completed
- [x] Storyboard breakdown completed
- [ ] 24 raw video clips checked in (awaiting on-prem generation)
- [ ] QA spot check passed (to run after on-prem video generation)

### Phase 3 (Post-Production Compositing and Sound)

- [x] Rough cut template and EDL timeline completed
- [x] Audio asset spec and example list completed
- [x] Post-production spec completed
- [ ] Actual voice-over / score / SFX generation completed
- [ ] Topaz 4K enhancement completed
- [ ] Defect repair completed

### Final Acceptance

- [x] 4K final delivery spec template completed
- [x] DaVinci color grading record template completed
- [x] Mix master record template completed
- [x] Topaz upscale and defect repair record template completed
- [x] ComfyUI workflow JSON packaging script completed
- [x] SOP manual template completed
- [x] Character asset library organization spec completed
- [x] Multi-platform release / tutorial / defense material template completed
- [ ] Actual final cut release and tech tutorial release (awaiting specific project execution)

---

## IV. Issues and Suggestions

| No. | Issue / Suggestion | Priority | Improvement plan | Owner |
|------|--------------------|----------|------------------|-------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

---

## V. Review Conclusion

- [ ] **Pass**: may proceed to the next phase
- [ ] **Conditional pass**: must revise per suggestions and re-review
- [ ] **Fail**: requires major revision and re-review

### Instructor / Mentor Comments

```
(Please fill in specific comments)
```

---

## VI. Signature Confirmation

| Role | Signature | Date |
|------|-----------|------|
| Instructor / Mentor | | |
| Project Producer / PM | | |
| Quality Director / QA | | |

---

> The original of this form is kept by the PM; a scan is synced to the project document library.
