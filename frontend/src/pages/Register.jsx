import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import AuthShell from "../components/AuthShell";
import { useAuth } from "../context/AuthContext";
import { apiError } from "../lib/api";

export default function Register() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    if (password.length < 8) {
      toast.error("Password must be at least 8 characters.");
      return;
    }
    setLoading(true);
    try {
      await register(email, password, name);
      toast.success("Account created. Welcome aboard.");
      navigate("/dashboard");
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell title="Provision an analyst" subtitle="// NEW ANALYST" testid="register-page">
      <form onSubmit={submit} className="space-y-4" data-testid="register-form">
        <Field label="Full name">
          <input required value={name} onChange={(e) => setName(e.target.value)} data-testid="register-name" className="input" placeholder="Jane Operative" />
        </Field>
        <Field label="Email">
          <input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} data-testid="register-email" className="input" placeholder="you@org.com" />
        </Field>
        <Field label="Password">
          <input required type="password" minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} data-testid="register-password" className="input" placeholder="At least 8 characters" />
        </Field>
        <button type="submit" disabled={loading} data-testid="register-submit"
          className="w-full bg-blue-500 hover:bg-blue-400 text-black font-mono font-bold tracking-widest uppercase text-xs py-3 rounded-sm transition-all duration-150 disabled:opacity-50">
          {loading ? "Provisioning…" : "Create Account"}
        </button>
        <div className="text-xs text-slate-500 font-mono">
          Already have access? <Link to="/login" className="text-blue-400" data-testid="login-link">Sign in</Link>
        </div>
      </form>
    </AuthShell>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="font-mono text-[10px] tracking-[0.25em] uppercase text-slate-400 mb-1.5 block">{label}</span>
      {children}
    </label>
  );
}
