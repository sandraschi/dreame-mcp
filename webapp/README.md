# Dreame dashboard (Vite + React)

Web UI for **dreame-mcp**: Dashboard, **Map** (LIDAR), Status, Controls, Settings, Help, and MCP tool hints.

**Dev:** `http://localhost:10895` — the Vite dev server proxies `/api` to the backend (default `http://localhost:10894`). Set `VITE_DREAME_API_BASE` if the API is on another host/port.

**Map page:** Renders the **`image`** field from `GET /api/v1/map` as a data URL. If the API only returns `raw_b64` (no `image`), the UI still shows the raw JSON; fix decode/render on the backend (see repo `docs/MAP_AND_ROBOTICS.md`).

Root **README** in the monorepo has `start` instructions and `DREAME_*` environment variables.

---

*Below: default Vite template notes (HMR, ESLint, etc.).*

# React + TypeScript + Vite (template)

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses Babel (or oxc with rolldown-vite) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev and build performance. To add it, see the [React Compiler installation docs](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

For a production app, consider enabling type-aware lint rules. See the default `eslint.config.js` and the [Vite + React + TS docs](https://vite.dev/).
