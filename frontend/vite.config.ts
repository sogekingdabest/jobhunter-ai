import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    headers: {
      "Cross-Origin-Embedder-Policy": "require-corp",
      "Cross-Origin-Opener-Policy": "same-origin",
    },
    proxy: {
      "/candidate-profiles": "http://127.0.0.1:8000",
      "/job-offers": "http://127.0.0.1:8000",
      "/match-assessments": "http://127.0.0.1:8000",
      "/tailored-resumes": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
  preview: {
    headers: {
      "Cross-Origin-Embedder-Policy": "require-corp",
      "Cross-Origin-Opener-Policy": "same-origin",
    },
  },
});
