/**
 * Next.js Instrumentation Hook (Next.js 14+, no experimental flag needed)
 * Auto-discovered oleh Next.js — init Sentry sesuai runtime
 * Docs: https://nextjs.org/docs/app/building-your-application/optimizing/instrumentation
 */
export async function register() {
  if (process.env.NEXT_RUNTIME === 'nodejs') {
    await import('./sentry.server.config');
  }

  if (process.env.NEXT_RUNTIME === 'edge') {
    // Edge runtime — tidak ada full Sentry support, skip
  }
}
