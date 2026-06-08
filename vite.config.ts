import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  root: "apps/client",
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "^/api/(health|materials|questions)(/.*)?$": "http://127.0.0.1:8000",
    },
  },
  build: {
    outDir: "../../dist/client",
    emptyOutDir: true,
  },
});
