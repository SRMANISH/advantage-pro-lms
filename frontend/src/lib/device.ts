const KEY = "ap_device_id";

/** Stable, device/browser-specific signals (no PII, low-entropy but consistent). */
function collectSignals(): string {
  const nav = navigator as Navigator & { deviceMemory?: number };
  const s = window.screen;
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone ?? "";
  return [
    nav.userAgent,
    nav.language,
    (nav.languages ?? []).join(","),
    String(nav.hardwareConcurrency ?? ""),
    String(nav.deviceMemory ?? ""),
    `${s.width}x${s.height}x${s.colorDepth}`,
    tz,
    canvasSignal(),
  ].join("|");
}

/** A canvas-rendering fingerprint — varies by GPU/driver/font stack across devices. */
function canvasSignal(): string {
  try {
    const c = document.createElement("canvas");
    const ctx = c.getContext("2d");
    if (!ctx) return "";
    ctx.textBaseline = "top";
    ctx.font = "14px Arial";
    ctx.fillStyle = "#069";
    ctx.fillText("AdvantagePro-device", 2, 2);
    return c.toDataURL();
  } catch {
    return "";
  }
}

async function sha256Hex(input: string): Promise<string> {
  try {
    const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(input));
    return Array.from(new Uint8Array(buf))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  } catch {
    // Insecure context (no SubtleCrypto): fall back to a non-crypto string hash.
    let h = 0;
    for (let i = 0; i < input.length; i++) h = (Math.imul(31, h) + input.charCodeAt(i)) | 0;
    return (h >>> 0).toString(16).padStart(8, "0");
  }
}

/**
 * A stable per-browser device identifier for the student device policy.
 *
 * Derived from device/browser signals (so it is consistent across sessions rather than a
 * throwaway random value) and then persisted. To strengthen this into spoof-resistant
 * identification, swap the body for a FingerprintJS visitorId — call sites already await,
 * so no other change is needed.
 */
export async function getDeviceId(): Promise<string> {
  const cached = localStorage.getItem(KEY);
  if (cached) return cached;
  const id = `fp_${await sha256Hex(collectSignals())}`;
  localStorage.setItem(KEY, id);
  return id;
}
