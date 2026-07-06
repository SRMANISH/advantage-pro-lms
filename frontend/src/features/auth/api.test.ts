import { vi } from "vitest";

import { api } from "../../lib/api";
import { authApi, TotpRequiredError } from "./api";

vi.mock("../../lib/api", () => ({ api: { post: vi.fn(), get: vi.fn() } }));
vi.mock("../../lib/device", () => ({ getDeviceId: async () => "test-device" }));

function axiosError(data: unknown) {
  return { isAxiosError: true, response: { data } };
}

describe("authApi.login", () => {
  it("resolves with the user on success", async () => {
    vi.mocked(api.post).mockResolvedValueOnce({ data: { id: "1", username: "s1" } });
    const user = await authApi.login("s1", "pw");
    expect(user).toEqual({ id: "1", username: "s1" });
  });

  it("throws TotpRequiredError when the backend signals totp_required", async () => {
    vi.mocked(api.post).mockRejectedValueOnce(
      axiosError({ detail: "Enter your code.", totp_required: true }),
    );
    await expect(authApi.login("adm", "pw")).rejects.toBeInstanceOf(TotpRequiredError);
  });

  it("throws a plain Error (not TotpRequiredError) for ordinary invalid credentials", async () => {
    vi.mocked(api.post).mockRejectedValueOnce(axiosError({ detail: "Invalid credentials." }));
    await expect(authApi.login("adm", "wrong")).rejects.toThrow("Invalid credentials.");
    vi.mocked(api.post).mockRejectedValueOnce(axiosError({ detail: "Invalid credentials." }));
    await expect(authApi.login("adm", "wrong")).rejects.not.toBeInstanceOf(TotpRequiredError);
  });

  it("passes totp_code through on the resubmit", async () => {
    vi.mocked(api.post).mockResolvedValueOnce({ data: { id: "1" } });
    await authApi.login("adm", "pw", "admin", "123456");
    expect(api.post).toHaveBeenCalledWith(
      "/auth/login/",
      expect.objectContaining({ totp_code: "123456" }),
    );
  });
});
