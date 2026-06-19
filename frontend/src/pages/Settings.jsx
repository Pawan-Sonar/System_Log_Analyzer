import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { ShieldCheck, QrCode, LockKey } from "@phosphor-icons/react";
import { api, apiError } from "../lib/api";
import { useAuth } from "../context/AuthContext";

export default function Settings() {
  const { user, refreshMe } = useAuth();
  const [setup, setSetup] = useState(null);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);

  const begin = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/auth/2fa/setup");
      setSetup(data);
    } catch (err) { toast.error(apiError(err)); }
    finally { setBusy(false); }
  };

  const verify = async () => {
    if (code.length !== 6) return toast.error("Enter the 6-digit code.");
    setBusy(true);
    try {
      await api.post("/auth/2fa/verify", { code });
      toast.success("Two-factor authentication enabled.");
      setSetup(null); setCode("");
      await refreshMe();
    } catch (err) { toast.error(apiError(err)); }
    finally { setBusy(false); }
  };

  const disable = async () => {
    if (code.length !== 6) return toast.error("Enter the 6-digit code to confirm.");
    setBusy(true);
    try {
      await api.post("/auth/2fa/disable", { code });
      toast.success("2FA disabled.");
      setCode("");
      await refreshMe();
    } catch (err) { toast.error(apiError(err)); }
    finally { setBusy(false); }
  };

  const enabled = user?.two_factor_enabled;

  return (
    <div className="space-y-5 anim-fade max-w-4xl" data-testid="settings-page">
      <div>
        <div className="section-label">// Account</div>
        <h1 className="font-mono text-3xl font-bold tracking-tight">Settings</h1>
      </div>

      <div className="card p-5" data-testid="profile-card">
        <div className="section-label mb-3">Profile</div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Info label="Name" value={user?.name} />
          <Info label="Email" value={user?.email} mono />
          <Info label="Role" value={(user?.role || "").toUpperCase()} mono />
        </div>
      </div>

      <div className="card p-5" data-testid="twofa-card">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <LockKey size={16} className="text-blue-400" />
            <div className="section-label">Two-Factor Authentication (TOTP)</div>
          </div>
          <span className={`badge-sev ${enabled ? "badge-low" : "badge-medium"}`} data-testid="twofa-status">
            {enabled ? "ENABLED" : "DISABLED"}
          </span>
        </div>

        <p className="text-xs text-slate-400 mb-4 max-w-xl">
          Use an authenticator app (Google Authenticator, Authy, 1Password) to generate
          time-based one-time codes for additional login security.
        </p>

        {!enabled && !setup && (
          <button onClick={begin} disabled={busy} data-testid="enable-2fa-btn"
            className="flex items-center gap-2 px-4 py-2 text-xs font-mono uppercase tracking-widest bg-blue-500 hover:bg-blue-400 text-black rounded-sm font-bold disabled:opacity-50">
            <ShieldCheck size={14}/> {busy ? "Generating…" : "Enable 2FA"}
          </button>
        )}

        {!enabled && setup && (
          <div className="space-y-4" data-testid="twofa-setup">
            <div className="flex flex-col md:flex-row gap-5 items-start">
              <div className="border border-slate-800 p-2 bg-white rounded-sm">
                <img src={setup.qr_code} alt="2FA QR" className="w-44 h-44" data-testid="twofa-qr" />
              </div>
              <div className="flex-1 space-y-3">
                <div>
                  <div className="section-label mb-1">Manual entry secret</div>
                  <code className="block font-mono text-xs text-blue-300 bg-black border border-slate-800 px-3 py-2 rounded-sm break-all" data-testid="twofa-secret">
                    {setup.secret}
                  </code>
                </div>
                <p className="text-xs text-slate-400">
                  1. Scan the QR code with your authenticator app.<br/>
                  2. Enter the 6-digit code below to confirm.
                </p>
                <div className="flex gap-2 items-end">
                  <label className="flex-1">
                    <span className="font-mono text-[9px] tracking-[0.25em] uppercase text-slate-500 mb-1 block">6-digit code</span>
                    <input value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                      maxLength={6} inputMode="numeric" data-testid="twofa-code"
                      className="input font-mono tracking-[0.4em] text-center" placeholder="000000" />
                  </label>
                  <button onClick={verify} disabled={busy} data-testid="twofa-verify"
                    className="px-4 py-2 text-xs font-mono uppercase tracking-widest bg-blue-500 hover:bg-blue-400 text-black rounded-sm font-bold disabled:opacity-50">
                    Verify
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {enabled && (
          <div className="space-y-3" data-testid="twofa-disable-block">
            <div className="text-xs text-slate-400">
              2FA is active. To disable, enter a current code from your authenticator.
            </div>
            <div className="flex gap-2 items-end max-w-md">
              <input value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                maxLength={6} inputMode="numeric" data-testid="twofa-disable-code"
                className="input font-mono tracking-[0.4em] text-center" placeholder="000000" />
              <button onClick={disable} disabled={busy} data-testid="twofa-disable-btn"
                className="px-4 py-2 text-xs font-mono uppercase tracking-widest border border-red-900 hover:border-red-500 text-red-300 hover:text-red-200 rounded-sm">
                Disable
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Info({ label, value, mono }) {
  return (
    <div>
      <div className="section-label">{label}</div>
      <div className={`mt-1 text-sm ${mono ? "font-mono" : ""} text-slate-100`}>{value || "—"}</div>
    </div>
  );
}
