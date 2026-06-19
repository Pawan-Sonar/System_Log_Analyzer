import React, { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import AuthShell from "../components/AuthShell";
import { api, apiError } from "../lib/api";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post("/auth/forgot-password", { email });
      setSent(true);
      toast.success("If that email exists, a reset link was sent.");
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell title="Recover access" subtitle="// PASSWORD RESET" testid="forgot-page">
      {sent ? (
        <div className="space-y-4" data-testid="forgot-success">
          <div className="border border-emerald-900 bg-emerald-500/5 p-4 rounded-sm">
            <div className="font-mono text-[10px] tracking-[0.25em] uppercase text-emerald-400 mb-1">RESET LINK DISPATCHED</div>
            <p className="text-sm text-slate-300">
              Check your inbox for further instructions. The link expires in 1 hour.
            </p>
            <p className="text-xs text-slate-500 mt-2 font-mono">
              Dev mode: reset link also logged to backend console.
            </p>
          </div>
          <Link to="/login" className="block text-center text-xs font-mono uppercase tracking-wider text-blue-400">← Back to sign in</Link>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4" data-testid="forgot-form">
          <label className="block">
            <span className="font-mono text-[10px] tracking-[0.25em] uppercase text-slate-400 mb-1.5 block">Email</span>
            <input required type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              data-testid="forgot-email" className="input" placeholder="you@org.com" />
          </label>
          <button type="submit" disabled={loading} data-testid="forgot-submit"
            className="w-full bg-blue-500 hover:bg-blue-400 text-black font-mono font-bold tracking-widest uppercase text-xs py-3 rounded-sm transition-all duration-150 disabled:opacity-50">
            {loading ? "Sending…" : "Send Reset Link"}
          </button>
          <div className="text-xs text-slate-500 font-mono">
            <Link to="/login" className="text-blue-400" data-testid="back-login">← Back to sign in</Link>
          </div>
        </form>
      )}
    </AuthShell>
  );
}
