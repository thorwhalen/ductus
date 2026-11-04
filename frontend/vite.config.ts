// Vite is the build tool: it serves the app during development with instant reload,
// and bundles it into `dist/` for production. Two settings matter here.
import { defineConfig, type Plugin } from 'vite'

/**
 * Social-preview tags, only when the deployment says where it lives.
 *
 * `og:image` must be an absolute URL (Slack, Discord and Facebook ignore a relative
 * one), and the URL is a fact about a deployment, not about this package. So the tags
 * are written only when `VITE_SITE_URL` is set at build time -- e.g.
 * `VITE_SITE_URL=https://example.com/ductus/` -- and a plain `npm run build` emits none
 * rather than a placeholder.
 */
function socialPreview(): Plugin {
  return {
    name: 'ductus-social-preview',
    transformIndexHtml(html) {
      const site = process.env.VITE_SITE_URL
      if (!site) return html
      const url = site.endsWith('/') ? site : `${site}/`
      const title = 'ductus'
      const description =
        'Paste a text and see which passages read as machine-written, and why.'
      const tags = [
        `<meta property="og:title" content="${title}" />`,
        `<meta property="og:description" content="${description}" />`,
        `<meta property="og:url" content="${url}" />`,
        `<meta property="og:image" content="${url}og-image.png" />`,
        '<meta property="og:image:width" content="1200" />',
        '<meta property="og:image:height" content="630" />',
        '<meta name="twitter:card" content="summary_large_image" />',
      ]
      return html.replace(/\s*<\/head>/, `\n${tags.map((t) => `    ${t}`).join('\n')}\n  </head>`)
    },
  }
}

export default defineConfig({
  plugins: [socialPreview()],
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
