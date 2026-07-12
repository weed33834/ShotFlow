# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-07-12

### Added

- **Flow-file-driven architecture**: ShotFlow provides SOP `.md` flow files that
  define the step-by-step orchestration for each output type. External agent
  frameworks (WorkBuddy, Yuanqi, Bailian, Dify) read these files and call
  ShotFlow tools for actual asset generation.
- **11 provider integrations**: Hunyuan Image, Hunyuan Video, Tencent TTS,
  Wanxiang (Wanx), Kling, Jimeng, Runway, HeyGen, Suno, Liblib, NovelAI.
  All providers implement the `BaseProvider` ABC and support `SIMULATE_MODE`
  for development and testing without API credentials.
- **REST API**: 7 endpoints covering generation, anchoring, assembly, spec
  management, and asset listing at `/api/v1/`.
- **MCP server**: 6 Model Context Protocol tools (`consistency_anchor`,
  `generate_image`, `generate_video`, `generate_audio`, `lip_sync`,
  `assemble`) for external agent frameworks to discover and invoke.
- **SOP flow files**: `make_video.sop.md`, `make_image_set.sop.md`,
  `make_comic.sop.md`, `make_micro_movie.sop.md`, `make_vn.sop.md` — each
  defining the complete step sequence for its output type.
- **Exposure package**: `integration/` directory containing MCP manifest,
  OpenAPI 3.0 spec, MCP Server Card v2.1, and agent integration guide.
- **ShotFlow Driver skill**: WorkBuddy skill (`shotflow-driver`) for
  one-command video generation from natural language prompts.
- **Original character "EggYolk"**: Copyright-clean character design with
  4 pose variants for meme-style short video production.
- **SIMULATE mode**: Full end-to-end validation without GPU or API keys.
  Verified: APP import, 6 MCP tools registered, POST /generate returns HTTP 200.

### Infrastructure

- Dependency lock: `fastapi==0.118.0`, `fastmcp-slim==3.4.4`,
  `starlette==0.45.3`, `httpx==0.28.1`.
- Database: SQLite (development) / PostgreSQL (production) via SQLAlchemy 2.0.
- Frontend: React + Vite + TypeScript, `/generate` page for one-click output.
- Dual remote: GitHub (primary) and GitCode (mirror).

### Security

- API keys stored in `.env` (gitignored).
- Secret key configurable via environment variable.
- CORS configurable through `.env`.
