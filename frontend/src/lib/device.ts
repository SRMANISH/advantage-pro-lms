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
 * Primary source is the FingerprintJS OSS visitorId — a richer, more stable fingerprint
 * (canvas/audio/font entropy, resilient to minor browser updates) than our hand-rolled
 * signal hash, which remains as the fallback when the library can't load (offline chunk,
 * old browser). Either way the id is **always derived fresh from live device signals** —
 * never persisted and read back — so copying a stored value to another machine does not
 * transfer the binding; the other machine computes its own fingerprint and is treated as a
 * new device (the point of the anti-sharing policy).
 *
 * Still a **deterrent, not tamper-proof identification** — a determined user can spoof
 * signals. The evasion-resistant upgrade is FingerprintJS Pro plus the server-side IP/UA
 * drift checks on the device-change request.
 */
export async function getDeviceId(): Promise<string> {
  try {
    const FingerprintJS = await import("@fingerprintjs/fingerprintjs");
    const agent = await FingerprintJS.load();
    const { visitorId } = await agent.get();
    if (visitorId) return `fpjs_${visitorId}`;
  } catch {
    // fall through to the signal hash
  }
  return `fp_${await sha256Hex(collectSignals())}`;
}
