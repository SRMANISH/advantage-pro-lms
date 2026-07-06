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
 * A per-browser device identifier for the student device policy.
 *
 * The id is **always derived fresh from the live device/browser signals** — we deliberately
 * do not persist it and read it back as identity. That means copying a stored value to
 * another machine does not transfer the binding: the other machine computes its own
 * fingerprint from its own signals and is treated as a new device (which is the whole point
 * of the anti-sharing policy). A browser/OS change legitimately re-triggers verification.
 *
 * This is a **deterrent, not tamper-proof identification** — a determined user can still
 * spoof the underlying signals. For stronger, evasion-resistant identification, drop in a
 * FingerprintJS Pro visitorId here (call sites already await, so nothing else changes) and
 * pair it with the server-side IP/UA drift signals on the device-change request.
 */
export async function getDeviceId(): Promise<string> {
  return `fp_${await sha256Hex(collectSignals())}`;
}
