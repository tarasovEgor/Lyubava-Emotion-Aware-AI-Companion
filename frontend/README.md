# Lyubava Frontend

React + Vite + TypeScript + Tailwind + shadcn/ui + TanStack Query + axios.

## Run

```bash
npm install
npm run dev
```

Open http://localhost:5173 — default route is `/chat`.

API requests go to `/api/*` (Vite proxy → `http://localhost:8000`).

## Chat mock

While backend chat endpoints are missing, chat uses an in-memory mock. Disable with:

```bash
# .env
VITE_CHAT_MOCK=false
```

## Pages

- `/chat` — chat with Lyubava
- `/admin` — metrics placeholder + disabled retrain button
