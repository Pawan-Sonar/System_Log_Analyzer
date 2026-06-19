import React, { useState } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import AuthShell from "../components/AuthShell";
import { api, apiError } from "../lib/api";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const [token, setToken] = useState(params.get("token") || "");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    if (password.length < 8) {
      toast.error("Password must be at least 8 characters.");
      return;
    }
    setLoading(true);
    try {
      await api.post("/auth/reset-password", { token, new_password: password });
      toast.success("Password updated. Please sign in.");
      navigate("/login");
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell title="Set new credentials" subtitle="// NEW PASSWORD" testid="reset-page">
      <form onSubmit={submit} className="space-y-4" data-testid="reset-form">
        <label className="block">
          <span className="font-mono text-[10px] tracking-[0.25em] uppercase text-slate-400 mb-1.5 block">Reset Token</span>
          <input required value={token} onChange={(e) => setToken(e.target.value)}
            data-testid="reset-token" className="input font-mono text-xs" placeholder="Paste your reset token" />
        </label>
        <label className="block">
          <span className="font-mono text-[10px] tracking-[0.25em] uppercase text-slate-400 mb-1.5 block">New Password</span>
          <input required type="password" minLength={8} value={password} onChange={(e) => setPassword(e.target.value)}
            data-testid="reset-password" className="input" placeholder="At least 8 characters" />
        </label>
        <button type="submit" disabled={loading} data-testid="reset-submit"
          className="w-full bg-blue-500 hover:bg-blue-400 text-black font-mono font-bold tracking-widest uppercase text-xs py-3 rounded-sm transition-all duration-150 disabled:opacity-50">
          {loading ? "Updating…" : "Update Password"}
        </button>
        <div className="text-xs text-slate-500 font-mono">
          <Link to="/login" className="text-blue-400" data-testid="back-login-reset">← Back to sign in</Link>
        </div>
      </form>
    </AuthShell>
  );
}
