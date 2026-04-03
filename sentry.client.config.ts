/**
 * Sentry Client-Side Configuration
 * Init Sentry di browser — error tracking untuk React components + user actions
 */
import * as Sentry from '@sentry/nextjs';

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,
    environment: process.env.NODE_ENV,

    // Tangkap 10% dari performance traces — cukup untuk pre-pilot
    tracesSampleRate: 0.1,
    // Replay hanya saat error (hemat bandwidth)
    replaysOnErrorSampleRate: 1.0,
    replaysSessionSampleRate: 0.0,

    // JANGAN kirim PII
    sendDefaultPii: false,

    integrations: [
      Sentry.replayIntegration({
        maskAllText: true,
        blockAllMedia: true,
      }),
    ],
  });
}
