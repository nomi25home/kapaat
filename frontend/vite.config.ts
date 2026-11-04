/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.svg", "apple-touch-icon.png"],
      manifest: {
        name: "Kapaat",
        short_name: "Kapaat",
        description: "Know what's in every bin.",
        theme_color: "#0f1923",
        background_color: "#0f1923",
        display: "standalone",
        start_url: "/",
        scope: "/",
        icons: [
          { src: "icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "icon-512.png", sizes: "512x512", type: "image/png" },
          { src: "maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
        shortcuts: [
          { name: "Scan", url: "/scan", icons: [{ src: "icon-192.png", sizes: "192x192" }] },
          { name: "Add item", url: "/add", icons: [{ src: "icon-192.png", sizes: "192x192" }] },
        ],
      },
      workbox: {
        navigateFallback: "/index.html",
        navigateFallbackDenylist: [/^\/api\//],
        runtimeCaching: [
          {
            // Read-only offline: last fetched inventory is shown when the network is down.
            urlPattern: ({ url, request }) =>
              url.pathname.startsWith("/api/") &&
              request.method === "GET" &&
              (!url.pathname.startsWith("/api/auth/") || url.pathname === "/api/auth/me") &&
              !url.pathname.startsWith("/api/labels/pdf") &&
              !url.pathname.startsWith("/api/export"),
            handler: "NetworkFirst",
            options: {
              cacheName: "kapaat-api",
              networkTimeoutSeconds: 4,
              expiration: { maxEntries: 300, maxAgeSeconds: 7 * 86400 },
            },
          },
        ],
      },
    }),
  ],
  server: {
    proxy: { "/api": { target: process.env.KAPAAT_API ?? "http://localhost:8000", changeOrigin: false } },
  },
  test: { environment: "jsdom" },
});
