import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { authService } from "../services/auth";
import { TokenResponse } from "../types/api";

describe("Admin Authentication Service & RBAC (In-Memory)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    authService.clear();
    localStorage.clear();
    sessionStorage.clear();
  });

  afterEach(() => {
    authService.clear();
    localStorage.clear();
    sessionStorage.clear();
  });

  it("authenticates admin and stores credentials strictly in-memory", async () => {
    const mockTokenResp: TokenResponse = {
      access_token: "jwt-access-token-123",
      refresh_token: "jwt-refresh-token-456",
      token_type: "bearer",
      expires_in_seconds: 900,
      role: "SITE_CURATOR",
      username: "curator_belur",
    };

    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockTokenResp), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    const result = await authService.login("curator_belur", "curator_secret");

    expect(result.access_token).toBe("jwt-access-token-123");
    expect(authService.isAuthenticated()).toBe(true);
    expect(authService.getAccessToken()).toBe("jwt-access-token-123");
    expect(authService.getRefreshToken()).toBe("jwt-refresh-token-456");
    expect(authService.getRole()).toBe("SITE_CURATOR");
    expect(authService.getUsername()).toBe("curator_belur");

    // Zero localStorage or sessionStorage footprint
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
    expect(localStorage.getItem("access_token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
  });

  it("enforces role hierarchy accurately", async () => {
    // 1. Viewer Role
    const viewerToken: TokenResponse = {
      access_token: "v-token",
      refresh_token: "v-refresh",
      token_type: "bearer",
      expires_in_seconds: 900,
      role: "VIEWER",
      username: "viewer_user",
    };

    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(viewerToken), { status: 200 })
    );
    await authService.login("viewer_user", "password");

    expect(authService.hasRole("VIEWER")).toBe(true);
    expect(authService.hasRole("OPERATOR")).toBe(false);
    expect(authService.hasRole("SITE_CURATOR")).toBe(false);
    expect(authService.hasRole("SUPER_ADMIN")).toBe(false);

    // 2. Operator Role
    authService.clear();
    const operatorToken: TokenResponse = {
      access_token: "o-token",
      refresh_token: "o-refresh",
      token_type: "bearer",
      expires_in_seconds: 900,
      role: "OPERATOR",
      username: "operator_user",
    };

    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(operatorToken), { status: 200 })
    );
    await authService.login("operator_user", "password");

    expect(authService.hasRole("VIEWER")).toBe(true);
    expect(authService.hasRole("OPERATOR")).toBe(true);
    expect(authService.hasRole("SITE_CURATOR")).toBe(false);

    // 3. Super Admin Role
    authService.clear();
    const adminToken: TokenResponse = {
      access_token: "s-token",
      refresh_token: "s-refresh",
      token_type: "bearer",
      expires_in_seconds: 900,
      role: "SUPER_ADMIN",
      username: "super_admin",
    };

    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(adminToken), { status: 200 })
    );
    await authService.login("super_admin", "password");

    expect(authService.hasRole("VIEWER")).toBe(true);
    expect(authService.hasRole("OPERATOR")).toBe(true);
    expect(authService.hasRole("SITE_CURATOR")).toBe(true);
    expect(authService.hasRole("SUPER_ADMIN")).toBe(true);
  });

  it("rotates token pair via refresh()", async () => {
    // Initial login
    const initialToken: TokenResponse = {
      access_token: "old-access",
      refresh_token: "old-refresh",
      token_type: "bearer",
      expires_in_seconds: 900,
      role: "OPERATOR",
      username: "operator_belur",
    };

    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(initialToken), { status: 200 })
    );
    await authService.login("operator_belur", "pass");

    // Perform refresh rotation
    const rotatedToken: TokenResponse = {
      access_token: "new-access",
      refresh_token: "new-refresh",
      token_type: "bearer",
      expires_in_seconds: 900,
      role: "OPERATOR",
      username: "operator_belur",
    };

    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(rotatedToken), { status: 200 })
    );

    const refreshResult = await authService.refresh();

    expect(refreshResult).not.toBeNull();
    expect(refreshResult?.access_token).toBe("new-access");
    expect(authService.getAccessToken()).toBe("new-access");
    expect(authService.getRefreshToken()).toBe("new-refresh");

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/auth/refresh"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ refresh_token: "old-refresh" }),
      })
    );
  });

  it("logout calls backend /auth/logout endpoint and wipes memory", async () => {
    const initialToken: TokenResponse = {
      access_token: "active-token",
      refresh_token: "active-refresh",
      token_type: "bearer",
      expires_in_seconds: 900,
      role: "SITE_CURATOR",
      username: "curator",
    };

    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(initialToken), { status: 200 })
    );
    await authService.login("curator", "pass");

    const logoutFetchSpy = vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ message: "Logged out" }), { status: 200 })
    );

    await authService.logout();

    expect(logoutFetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/auth/logout"),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer active-token",
        }),
      })
    );

    expect(authService.isAuthenticated()).toBe(false);
    expect(authService.getAccessToken()).toBeNull();
    expect(authService.getRefreshToken()).toBeNull();
    expect(authService.getRole()).toBeNull();
  });

  it("rejects login with backend error message", async () => {
    const errorEnvelope = {
      error: {
        code: "UNAUTHORIZED",
        message: "Invalid administrative credentials.",
      },
    };

    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(errorEnvelope), { status: 401 })
    );

    await expect(authService.login("bad_user", "bad_pass")).rejects.toThrow(
      "Invalid administrative credentials."
    );
    expect(authService.isAuthenticated()).toBe(false);
  });

  it("notifies subscribed listeners on state transitions", async () => {
    const listener = vi.fn();
    const unsubscribe = authService.subscribe(listener);

    // Initial invocation
    expect(listener).toHaveBeenCalledWith(false, null);

    // On login
    const tokenResp: TokenResponse = {
      access_token: "token-1",
      refresh_token: "refresh-1",
      token_type: "bearer",
      expires_in_seconds: 900,
      role: "VIEWER",
      username: "viewer",
    };

    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(tokenResp), { status: 200 })
    );
    await authService.login("viewer", "pass");

    expect(listener).toHaveBeenCalledWith(true, "VIEWER");

    // On clear
    authService.clear();
    expect(listener).toHaveBeenCalledWith(false, null);

    unsubscribe();
  });
});
