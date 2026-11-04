/// <reference types="vite/client" />

interface ImportMetaEnv {
  /**
   * Where the API lives, when it is not the origin the page was served from. Empty
   * (the default) makes every request relative, which is right when `ductus-http`
   * serves the built assets itself. A host that mounts the UI and the API under
   * different prefixes sets it at build time, e.g. `VITE_DUCTUS_API_BASE=/api/ductus`.
   */
  readonly VITE_DUCTUS_API_BASE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
