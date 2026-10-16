import React, { useState } from "react";
import { Lock, User, AlertCircle, ArrowLeft, ShieldCheck, Loader2 } from "lucide-react";
import { authService } from "@/services/auth";

interface AdminLoginProps {
  onSuccess: () => void;
  onCancel: () => void;
}

export const AdminLogin: React.FC<AdminLoginProps> = ({ onSuccess, onCancel }) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setErrorMessage("Please enter both username and password.");
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      await authService.login(username.trim(), password);
      onSuccess();
    } catch (err: any) {
      setErrorMessage(err.message || "Invalid administrative credentials.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-heritage-ivory dark:bg-heritage-basalt flex flex-col justify-center py-12 sm:px-6 lg:px-8 text-heritage-brown dark:text-heritage-marble transition-colors">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        {/* Back to Tourist Guide Button */}
        <button
          onClick={onCancel}
          type="button"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-heritage-umber dark:text-heritage-stone hover:text-heritage-brown dark:hover:text-heritage-gold mb-6 transition-colors focus:ring-2 focus:ring-heritage-gold rounded p-1"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Tourist Guide</span>
        </button>

        {/* Temple Crest & Title */}
        <div className="text-center">
          <div className="inline-flex p-3 rounded-full bg-heritage-gold/10 dark:bg-heritage-gold/20 text-heritage-gold mb-3">
            <Lock className="w-8 h-8" />
          </div>
          <h2 className="text-2xl font-bold font-display tracking-tight text-heritage-brown dark:text-heritage-marble">
            Heritage Administrator Portal
          </h2>
          <p className="mt-1.5 text-xs text-heritage-umber dark:text-heritage-stone">
            Belur Chennakeshava Temple • Knowledge Base & Model Governance
          </p>
        </div>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4">
        <div className="bg-white dark:bg-heritage-stone-dark py-8 px-6 shadow-xl rounded-xl border border-heritage-brown/10 dark:border-heritage-gold/20 sm:px-10">
          {/* Security Notice */}
          <div className="mb-6 p-3 rounded-lg bg-heritage-gold/10 dark:bg-heritage-gold/15 border border-heritage-gold/20 text-heritage-brown dark:text-heritage-gold text-xs flex items-start gap-2.5">
            <ShieldCheck className="w-4 h-4 flex-shrink-0 mt-0.5 text-heritage-gold" />
            <span>
              <strong>Zero-Storage Protocol:</strong> Authentication tokens are maintained strictly in volatile memory. No credentials or session tokens are written to browser storage.
            </span>
          </div>

          {/* Error Banner */}
          {errorMessage && (
            <div
              role="alert"
              className="mb-6 p-3 rounded-lg bg-heritage-terracotta/10 border border-heritage-terracotta/30 text-heritage-terracotta dark:text-red-300 text-xs flex items-center gap-2 animate-in fade-in duration-200"
            >
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5" noValidate>
            <div>
              <label
                htmlFor="admin-username"
                className="block text-xs font-semibold text-heritage-brown dark:text-heritage-marble uppercase tracking-wider"
              >
                Username or Email
              </label>
              <div className="mt-1.5 relative rounded-md shadow-xs">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-heritage-umber dark:text-heritage-stone">
                  <User className="w-4 h-4" />
                </div>
                <input
                  id="admin-username"
                  name="username"
                  type="text"
                  autoComplete="username"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="admin or curator"
                  disabled={isLoading}
                  className="block w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-heritage-brown/20 dark:border-heritage-gold/20 bg-heritage-ivory dark:bg-heritage-carved-basalt text-heritage-brown dark:text-heritage-marble placeholder-heritage-umber/60 dark:placeholder-heritage-stone/60 focus:outline-hidden focus:ring-2 focus:ring-heritage-gold focus:border-transparent transition-colors"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="admin-password"
                className="block text-xs font-semibold text-heritage-brown dark:text-heritage-marble uppercase tracking-wider"
              >
                Password
              </label>
              <div className="mt-1.5 relative rounded-md shadow-xs">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-heritage-umber dark:text-heritage-stone">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  id="admin-password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  disabled={isLoading}
                  className="block w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-heritage-brown/20 dark:border-heritage-gold/20 bg-heritage-ivory dark:bg-heritage-carved-basalt text-heritage-brown dark:text-heritage-marble placeholder-heritage-umber/60 dark:placeholder-heritage-stone/60 focus:outline-hidden focus:ring-2 focus:ring-heritage-gold focus:border-transparent transition-colors"
                />
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex justify-center items-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-semibold text-heritage-midnight-basalt bg-heritage-gold hover:bg-heritage-gold-radiant focus:outline-hidden focus:ring-2 focus:ring-offset-2 focus:ring-heritage-gold disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    <span>Verifying Credentials...</span>
                  </>
                ) : (
                  <span>Access Dashboard</span>
                )}
              </button>
            </div>
          </form>

          <div className="mt-6 pt-4 border-t border-heritage-brown/10 dark:border-heritage-gold/15 text-center">
            <p className="text-[11px] text-heritage-umber dark:text-heritage-stone">
              Supported Roles: <strong>SUPER_ADMIN</strong> • <strong>SITE_CURATOR</strong> • <strong>OPERATOR</strong> • <strong>VIEWER</strong>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
