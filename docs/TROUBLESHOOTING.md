# FAQ

English (current) | [中文](./TROUBLESHOOTING.zh.md)

> This file collects issues you may encounter while using ShotFlow and their solutions.

---

## Environment Deployment

### Q: `deploy_comfyui.sh` fails to run

**Possible causes**:
- No NVIDIA GPU, or driver not installed;
- Git not installed, or network unreachable;
- Python version lower than 3.10.

**Solution**:
- Verify GPU and driver: `nvidia-smi`;
- Verify Python version: `python3 --version`;
- Check network; use a HuggingFace mirror or pre-download models if needed.

---

### Q: `preflight_check.py` reports GPU unavailable

**Possible causes**:
- No CUDA on the current machine;
- PyTorch was installed as the CPU version.

**Solution**:
- With GPU: reinstall the CUDA version of PyTorch, see https://pytorch.org;
- Without GPU: switch to a cloud API workflow, running only scripts and post-production.

---

## Character Consistency

### Q: Ava looks different across shots

**Solution**:
- Check whether the character bible has pinned all anchor points;
- Confirm IPAdapter reference images cover multiple angles (front/side/back);
- Raise the IPAdapter weight to 0.8–1.0;
- Add `inconsistent hairstyle, wrong clothing` to the negative prompt;
- Run blind tests; re-roll any shots that do not meet the standard.

---

### Q: Keyframes show extra fingers or deformed faces

**Solution**:
- Add `extra fingers, mutated hands, deformed face` to the negative prompt;
- Lower CFG or increase sampling steps;
- Use ADetailer or similar nodes for local repair.

---

## Video Generation

### Q: Severe video flickering

**Solution**:
- Check whether keyframes and video prompts are consistent;
- Use the Wan2.2 Low Noise expert to repair broken frames;
- Lower motion-amplitude prompts;
- After output, apply temporal denoising with Topaz or FFmpeg.

---

### Q: Kling API call fails

**Solution**:
- Confirm `KLING_API_KEY` is configured in `.env`;
- Check whether API quota is sufficient;
- Review the official Kling docs to confirm API version and parameter format.

---

## Post-Production and Audio

### Q: ElevenLabs voiceover emotion is off

**Solution**:
- Switch the voice ID to one closer to the character setting;
- Adjust the stability and similarity parameters;
- Add emotion tags to the lines, such as `[whisper]`, `[angry]`.

---

### Q: Suno-generated music does not match the style

**Solution**:
- Specify style, mood, and instruments explicitly in the prompt;
- Use the reference-audio feature;
- Generate several tracks and pick the best.

---

## Repository and Collaboration

### Q: `sync_repos.sh` push fails

**Solution**:
- Confirm the remote URL in `.git/config` does not contain a hardcoded Token (recommended: use SSH or a Git credential manager);
  - HTTPS + credential manager: `git config --global credential.helper store` (auto-saved after first entry)
  - SSH: `git remote set-url github git@github.com:MS33834/ShotFlow.git`
- For GitCode, keep the URL as `https://gitcode.com/badhope/ShotFlow.git`; the Token is supplied by the credential manager;
- Check the network connection.

---

### Q: Accidentally committed an API key to the repository

**Solution**:
- Revoke the key immediately;
- Use `git filter-repo` or BFG to clean the history;
- Regenerate the key and write it into `.env`.

---

## Others

### Q: Can the project run on CPU?

**Answer**: Scripts and post-production can run, but video generation will be very slow. We recommend at least an RTX 3090 24GB or a cloud API.

---

> If the above does not solve your issue, feel free to submit an Issue.
