import React, { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { toast } from "sonner";
import AuthShell from "../components/AuthShell";
import { useAuth } from "../context/AuthContext";
import { apiError } from "../lib/api";
import { Eye, EyeSlash } from "@phosphor-icons/react";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [needs2fa, setNeeds2fa] = useState(false);
  const [otp, setOtp] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || "/dashboard";

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email, password, needs2fa ? otp : undefined);
      toast.success("Welcome back, analyst.");
      navigate(from, { replace: true });
    } catch (err) {
      const msg = apiError(err);
      if (msg.toLowerCase().includes("2fa")) {
        setNeeds2fa(true);
        toast("2FA code required");
      } else {
        toast.error(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell title="Access the console" subtitle="// AUTHENTICATE" testid="login-page">
      <form onSubmit={submit} className="space-y-4" data-testid="login-form">
        <Field label="Email" htmlFor="email">
          <input
            id="email" type="email" required autoComplete="email"
            data-testid="login-email"
            value={email} onChange={(e) => setEmail(e.target.value)}
            className="input"
            placeholder="analyst@company.com"
          />
        </Field>
        <Field label="Password" htmlFor="password">
          <div className="relative">
            <input
              id="password" type={show ? "text" : "password"} required autoComplete="current-password"
              data-testid="login-password"
              value={password} onChange={(e) => setPassword(e.target.value)}
              className="input pr-10"
              placeholder="••••••••"
            />
            <button type="button" onClick={() => setShow((s) => !s)}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-100"
              data-testid="toggle-password">
              {show ? <EyeSlash size={16} /> : <Eye size={16} />}
            </button>
          </div>
        </Field>

        {needs2fa && (
          <Field label="2FA Code" htmlFor="totp">
            <input
              id="totp" inputMode="numeric" pattern="[0-9]{6}" maxLength={6}
              data-testid="login-totp" value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
              className="input font-mono tracking-[0.5em] text-center"
              placeholder="000000"
            />
          </Field>
        )}

        <div className="flex items-center justify-between text-xs">
          <Link to="/forgot-password" className="text-slate-400 hover:text-blue-400 font-mono uppercase tracking-wider" data-testid="forgot-link">
            Forgot password?
          </Link>
          <Link to="/register" className="text-slate-400 hover:text-blue-400 font-mono uppercase tracking-wider" data-testid="register-link">
            Create account →
          </Link>
        </div>

        <button type="submit" disabled={loading}
          data-testid="login-submit"
          className="w-full bg-blue-500 hover:bg-blue-400 text-black font-mono font-bold tracking-widest uppercase text-xs py-3 rounded-sm transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed">
          {loading ? "Authenticating…" : "Sign In"}
        </button>

        <div className="pt-4 mt-4 border-t border-slate-800/80 text-xs text-slate-500 font-mono">
          Demo: <span className="text-slate-300">admin@soc.com</span> / <span className="text-slate-300">Admin@123</span>
        </div>
      </form>
    </AuthShell>
  );
}

function Field({ label, htmlFor, children }) {
  return (
    <label htmlFor={htmlFor} className="block">
      <span className="font-mono text-[10px] tracking-[0.25em] uppercase text-slate-400 mb-1.5 block">{label}</span>
      {children}
    </label>
  );
}
