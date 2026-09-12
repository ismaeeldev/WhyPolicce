"use client";

import { ErrorContent } from "@/components/shared/ErrorContent";

/**
 * Route-segment error boundary — catches render/data errors thrown inside
 * app/ (below the root layout). Next.js requires this file to be a client
 * component and to receive exactly {error, reset} as props; it cannot use
 * generateMetadata (see global-error.tsx for the one case this file can't
 * cover: an error thrown by the root layout itself).
 */
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return <ErrorContent error={error} reset={reset} />;
}
