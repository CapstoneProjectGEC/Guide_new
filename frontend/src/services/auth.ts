/**
 * Secure In-Memory Admin Authentication Service.
 *
 * Security Guarantees:
 * - Zero storage in localStorage, sessionStorage, or client cookies.
 * - Tokens reside exclusively in Javascript memory.
 * - Rotating refresh token lifecycle adhering strictly to the backend FastAPI contract.
 * - Role-Based Access Control (RBAC) hierarchy matching backend definitions:
 *   SUPER_ADMIN (4) > SITE_CURATOR (3) > OPERATOR (2) > VIEWER (1).
 */

import { AdminRoleType, TokenResponse } from "@/types/api";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api/v1";

export const ROLE_HIERARCHY: Record<AdminRoleType, number> = {
  VIEWER: 1,
  OPERATOR: 2,
  SITE_CURATOR: 3,
  SUPER_ADMIN: 4,
};

type AuthListener = (isAuthenticated: boolean, role: AdminRoleType | null) => void;

class AuthService {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private currentRole: AdminRoleType | null = null;
  private currentUsername: string | null = null;
  private tokenExpiresAt: number | null = null; // epoch ms
  private listeners: Set<AuthListener> = new Set();
  private refreshPromise: Promise<TokenResponse | null> | null = null;

  /**
   * Subscribe to authentication state transitions.
   */
  public subscribe(listener: AuthListener): () => void {
    this.listeners.add(listener);
    // Initial notify
    listener(this.isAuthenticated(), this.currentRole);
    return () => {
      this.listeners.delete(listener);
    };
  }

  private notify(): void {
    const authenticated = this.isAuthenticated();
    for (const listener of this.listeners) {
      try {
        listener(authenticated, this.currentRole);
      } catch (err) {
        console.error("Auth listener notification failed:", err);
      }
    }
  }

  /**
   * Verify if active access token exists and has not expired.
   */
  public isAuthenticated(): boolean {
    if (!this.accessToken) return false;
    if (this.tokenExpiresAt && Date.now() >= this.tokenExpiresAt - 5000) {
      // Considered expired if within 5 seconds of expiry
      return false;
    }
    return true;
  }

  public getAccessToken(): string | null {
    return this.accessToken;
  }

  public getRefreshToken(): string | null {
    return this.refreshToken;
  }

  public getRole(): AdminRoleType | null {
    return this.currentRole;
  }

  public getUsername(): string | null {
    return this.currentUsername;
  }

  /**
   * Evaluates if current authenticated administrator meets or exceeds required privilege level.
   */
  public hasRole(minRole: AdminRoleType): boolean {
    if (!this.currentRole) return false;
    const currentLevel = ROLE_HIERARCHY[this.currentRole] || 0;
    const requiredLevel = ROLE_HIERARCHY[minRole] || 999;
    return currentLevel >= requiredLevel;
  }

  /**
   * Authenticate with administrator username/password.
   */
  public async login(username: string, password: string): Promise<TokenResponse> {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      let errMsg = "Authentication failed.";
      try {
        const errorData = await response.json();
        if (errorData?.error?.message) {
          errMsg = errorData.error.message;
        }
      } catch {
        // Non-JSON error
      }
      throw new Error(errMsg);
    }

    const tokenData: TokenResponse = await response.json();
    this.setTokens(tokenData);
    return tokenData;
  }

  /**
   * Rotate access and refresh tokens via backend /auth/refresh endpoint.
   * Uses lock promise to prevent race conditions during concurrent 401s.
   */
  public async refresh(): Promise<TokenResponse | null> {
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    if (!this.refreshToken) {
      this.clear();
      return null;
    }

    this.refreshPromise = (async () => {
      try {
        const response = await fetch(`${API_BASE}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: this.refreshToken }),
        });

        if (!response.ok) {
          this.clear();
          return null;
        }

        const tokenData: TokenResponse = await response.json();
        this.setTokens(tokenData);
        return tokenData;
      } catch (err) {
        this.clear();
        return null;
      } finally {
        this.refreshPromise = null;
      }
    })();

    return this.refreshPromise;
  }

  /**
   * Explicit administrator logout. Calls backend audit logging then clears in-memory state.
   */
  public async logout(): Promise<void> {
    const token = this.accessToken;
    this.clear();

    if (token) {
      try {
        await fetch(`${API_BASE}/auth/logout`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        });
      } catch (err) {
        console.warn("Backend logout notification encountered network issue:", err);
      }
    }
  }

  private setTokens(data: TokenResponse): void {
    this.accessToken = data.access_token;
    this.refreshToken = data.refresh_token;
    this.currentRole = data.role;
    this.currentUsername = data.username;
    this.tokenExpiresAt = Date.now() + data.expires_in_seconds * 1000;
    this.notify();
  }

  /**
   * Reset all in-memory credentials and notify listeners.
   */
  public clear(): void {
    this.accessToken = null;
    this.refreshToken = null;
    this.currentRole = null;
    this.currentUsername = null;
    this.tokenExpiresAt = null;
    this.notify();
  }
}

export const authService = new AuthService();
