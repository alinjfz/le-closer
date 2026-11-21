import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  const backend = env.LECLOSER_API_PROXY || "http://localhost:8003";
  return {
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    watch: { usePolling: env.LECLOSER_POLLING === "true", interval: 300 },
    proxy: {
      "/calls": { target: backend, changeOrigin: true },
      "/ws": { target: backend.replace(/^http/, "ws"), ws: true },
      "/health": { target: backend, changeOrigin: true },
    },
  },
  };
});
