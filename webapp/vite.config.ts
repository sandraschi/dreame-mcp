import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
	plugins: [react()],
	resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
	server: {
		port: 10795,
		strictPort: true,
		host: true,
		proxy: {
			"/api": { target: "http://localhost:10794", changeOrigin: true },
		},
	},
});
