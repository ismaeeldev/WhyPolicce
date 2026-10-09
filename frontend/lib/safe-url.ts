/**
 * Link/redirect hygiene for values that come from users or the query string.
 * Rendering an unchecked string into an href lets `javascript:` URLs run script;
 * passing an unchecked `returnTo` onward can bounce someone to another site.
 */

/** Absolute http(s) URL, or null. A bare "yourfirm.com" gets https:// prepended. */
export function safeExternalUrl(raw: string | null | undefined): string | null {
  const value = raw?.trim();
  if (!value) return null;
  try {
    // "javascript:alert(1)" has a scheme but no "//", so don't treat it as a host.
    const hasScheme = /^[a-z][a-z0-9+.-]*:/i.test(value) && !/^[^/]*:\d+(\/|$)/.test(value);
    const url = new URL(hasScheme ? value : `https://${value}`);
    return url.protocol === "http:" || url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
}

/** Host without "www.", for showing a link's label. */
export function displayHost(url: string): string {
  try {
    return new URL(url).host.replace(/^www\./, "");
  } catch {
    return url;
  }
}

/** Same-site path only ("/x"), never "//host", "/\host" or an absolute URL. */
export function safeReturnTo(raw: string | null | undefined): string | undefined {
  return raw && /^\/(?![/\\])/.test(raw) ? raw : undefined;
}

/** Stripe Checkout URLs are always https. */
export function isHttpsUrl(raw: string | null | undefined): raw is string {
  try {
    return !!raw && new URL(raw).protocol === "https:";
  } catch {
    return false;
  }
}
