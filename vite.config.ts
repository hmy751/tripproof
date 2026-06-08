import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  root: "src/client",
  plugins: [react(), tailwindcss()],
  server: {
    fs: {
      allow: ["../../src"],
    },
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
  build: {
    outDir: "../../dist/client",
    emptyOutDir: true,
  },
});
