import { nextPollInterval, signatureOf } from "./NotificationBell";

describe("signatureOf", () => {
  it("differs when an item's read state changes", () => {
    const a = [{ id: "1", kind: "k", message: "m", link: "", read: false, created_at: "" }];
    const b = [{ id: "1", kind: "k", message: "m", link: "", read: true, created_at: "" }];
    expect(signatureOf(a)).not.toBe(signatureOf(b));
  });

  it("is stable for an unchanged list", () => {
    const items = [{ id: "1", kind: "k", message: "m", link: "", read: false, created_at: "" }];
    expect(signatureOf(items)).toBe(signatureOf(items));
  });

  it("is empty for no notifications", () => {
    expect(signatureOf([])).toBe("");
  });
});

describe("nextPollInterval", () => {
  it("starts at the base interval", () => {
    expect(nextPollInterval(0)).toBe(20_000);
  });

  it("doubles per quiet poll", () => {
    expect(nextPollInterval(1)).toBe(40_000);
    expect(nextPollInterval(2)).toBe(80_000);
    expect(nextPollInterval(3)).toBe(160_000);
  });

  it("caps at 5 minutes however long the quiet streak", () => {
    expect(nextPollInterval(10)).toBe(300_000);
    expect(nextPollInterval(50)).toBe(300_000);
  });
});
