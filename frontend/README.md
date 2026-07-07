# ShotFlow frontend

React 18 + TypeScript + Vite + Ant Design Pro admin console for the ShotFlow pipeline.
Covers projects, shots, keyframes, render queue (SSE real-time), workflows, audio, QA,
and case studies.

## Stack

- **React 18 + TypeScript** — UI
- **Vite** — dev server + build
- **Ant Design Pro** — component library
- **TanStack Query** — server state, cache invalidation
- **Axios** — HTTP client, JWT in `sessionStorage` under `shotflow_token`
- **Nginx** — production static host + reverse proxy to backend

## Layout

```
frontend/
├── src/
│   ├── api/             # axios client + per-resource hooks
│   ├── components/      # ProtectedRoute, StatusTag
│   ├── contexts/        # AuthContext
│   ├── hooks/           # useQueueStream (SSE)
│   ├── layouts/         # MainLayout (sidebar + header)
│   ├── pages/           # one file per route
│   ├── styles/          # global.css
│   ├── types/           # shared types (kept in sync with backend schemas)
│   ├── App.tsx          # routes
│   └── main.tsx         # entry
├── .eslintrc.cjs
├── Dockerfile           # multi-stage: node build → nginx serve
├── nginx.conf
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## Quick start

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173 (proxied to backend :8000)
npm run build        # production bundle → dist/
npm run typecheck    # tsc --noEmit
npm run lint         # eslint
```

Default dev login: see backend/init_db.py output for seeded credentials.

## Environment

Create `.env.local` (Vite reads `VITE_`-prefixed vars):

```
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

See [`.env.example`](./.env.example) for the full list.

## Routes

| Path | Page |
|------|------|
| `/login` | Login (JWT) |
| `/dashboard` | Overview (health + queue stats + projects) |
| `/projects` | Project CRUD |
| `/shots` | Shot management |
| `/keyframes` | Keyframe management |
| `/queue` | Render queue (SSE + submit/retry/cancel) |
| `/workflows` | ComfyUI workflow management |
| `/workflow-configs` | YAML config + provider scoring |
| `/assets` | Asset gallery |
| `/audio` | Dialogue & voiceover |
| `/qa` | QA reports |
| `/case-studies` | Case study showcase |

## Notes

- SSE reconnect uses exponential backoff in `useQueueStream`.
- `types/index.ts` mirrors backend `schemas/` — update both sides when the API changes.
- Nginx build disables SSE proxy buffering (`proxy_buffering off`).
