// Vite is the build tool: it serves the app during development with instant reload,
// and bundles it into `dist/` for production. Two settings matter here.
import { defineConfig } from 'vite'

export default defineConfig({
  // `base: './'` makes the built asset URLs relative, so `dist/` works wherever it is
  // mounted -- which is what lets `ductus.http.mk_app(ui=...)` serve it at `/`.
  base: './',
  server: {
    // In development the app runs on Vite's port and the API on uvicorn's. This
    // forwards API calls to uvicorn so the browser still sees one origin and there
    // is no CORS to configure. In production there is one server and no proxy.
    proxy: Object.fromEntries(
      ['/gauge', '/detectors', '/segmenters', '/tells', '/openapi.json'].map((path) => [
        path,
        { target: 'http://127.0.0.1:8000', changeOrigin: true },
      ]),
    ),
  },
})
