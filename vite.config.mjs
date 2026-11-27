import { defineConfig } from "vite";

export default defineConfig({
  publicDir: false,
  build: {
    outDir: "frontend/dist",
    lib: {
      entry: "frontend/site.ts",
      name: "ShsoFrontend",
      formats: ["iife"],
      fileName: () => "js/site.js",
    },
  },
});
