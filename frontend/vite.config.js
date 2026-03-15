import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],

  server: {
    port: 5173,
    proxy: {
      // In dev, Vite proxies /api/** to the local FastAPI server.
      // In production, Firebase Hosting rewrites /api/** to Cloud Run.
      "/api": {
        target: "http://localhost:8080",
        changeOrigin: true,
      },
    },
  },

  build: {
    outDir: "dist",
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          // Split React into its own chunk — cached across deploys
          vendor: ["react", "react-dom"],
        },
      },
    },
  },
});
