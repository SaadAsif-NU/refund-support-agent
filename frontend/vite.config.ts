import { defineConfig, type PluginOption } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Backend (FastAPI) owns the REST + WebSocket APIs. In dev, Vite serves the
// app on :5173 and proxies /api and /ws to the backend on :8000.
const BACKEND = "http://127.0.0.1:8000";

// Serve admin.html at the pretty URL "/admin" in dev, matching how FastAPI
// serves it in production (so the app's "/admin" links work in both).
function adminPrettyUrl(): PluginOption {
  return {
    name: "admin-pretty-url",
    configureServer(server) {
      server.middlewares.use((req, _res, next) => {
        // `req` is contextually typed as Node's IncomingMessage, whose `url`
        // isn't visible without @types/node — reach it via a small cast.
        const proxied = req as unknown as { url?: string };
        if (proxied.url === "/admin" || proxied.url === "/admin/") {
          proxied.url = "/admin.html";
        }
        next();
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), tailwindcss(), adminPrettyUrl()],
  server: {
    proxy: {
      "/api": BACKEND,
      "/ws": { target: BACKEND, ws: true },
    },
  },
  build: {
    // Multi-page app: one bundle per page, mirroring the two FastAPI routes.
    // Input paths are resolved relative to the project root (this directory).
    rollupOptions: {
      input: {
        customer: "index.html",
        admin: "admin.html",
      },
    },
  },
});
