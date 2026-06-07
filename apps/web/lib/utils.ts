import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format a date/ISO string consistently on both server and client.
 *
 * Using an explicit locale ("en-GB") and fixed options prevents the hydration
 * mismatch that occurs when Node's default locale differs from the browser's
 * (e.g. server renders "07/06/2026, 10:27:44", browser renders "6/7/2026, 10:27:44 AM").
 *
 * Pair with `suppressHydrationWarning` on the containing element for belt-and-braces
 * protection when this value is rendered inside an SSR'd client component.
 */
export function fmtDate(isoString: string | null | undefined): string {
  if (!isoString) return "—";
  try {
    return new Intl.DateTimeFormat("en-GB", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    }).format(new Date(isoString));
  } catch {
    return isoString;
  }
}
