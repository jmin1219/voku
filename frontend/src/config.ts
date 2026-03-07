/**
 * Voku frontend configuration.
 *
 * API_BASE is read from environment (set via VITE_API_BASE in .env)
 * with fallback to localhost for development.
 */
export const API_BASE =
  import.meta.env.VITE_API_BASE || "http://localhost:8000/api";
