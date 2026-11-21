import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/calls": { target: "http://localhost:8003", changeOrigin: true },
      "/ws": { target: "ws://localhost:8003", ws: true },
      "/health": { target: "http://localhost:8003", changeOrigin: true },
    },
  },
});
