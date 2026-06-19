import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { MagnifyingGlass, MapPin, Lightning, Clock } from "@phosphor-icons/react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { api, apiError } from "../lib/api";
import SeverityBadge from "../components/SeverityBadge";

export default function Investigation() {
  const { ip: ipParam } = useParams();
  const navigate = useNavigate();
  const [ip, setIp] = useState(ipParam || "");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [alerts, setAlerts] = useState([]);

  const lookup = async (queryIp) => {
    const targetIp = (queryIp || ip || "").trim();
    if (!targetIp) return;
    setLoading(true);
    try {
      const [{ data: d }, { data: a }] = await Promise.all([
        api.get(`/logs/by-ip/${encodeURIComponent(targetIp)}`),
        api.get(`/alerts?limit=200`),
      ]);
      setData(d);
      setAlerts((a.items || []).filter((x) => x.ip_address === targetIp));
    } catch (err) {
      toast.error(apiError(err));
    } finally { setLoading(false); }
  };

  useEffect(() => {
    if (ipParam) {
      setIp(ipParam);
      lookup(ipParam);
    }
  }, [ipParam]);

  const submit = (e) => {
    e.preventDefault();
    if (ip) navigate(`/investigation/${ip}`);
  };

  // Build timeline
  const timeline = (data?.items || []).slice().reverse().map((it, i) => ({
    idx: i, ts: it.timestamp.slice(11, 16),
    status: it.status === "failure" ? 0 : 1,
    label: `${it.timestamp.slice(11, 16)} ${it.username} ${it.event_type}`,
  }));

  const failures = (data?.items || []).filter((l) => l.status === "failure").length;
  const successes = (data?.items || []).filter((l) => l.status === "success").length;
  const uniqueUsers = new Set((data?.items || []).map((l) => l.username)).size;

  return (
    <div className="space-y-5 anim-fade" data-testid="investigation-page">
      <div>
        <div className="section-label">// Forensics</div>
        <h1 className="font-mono text-3xl font-bold tracking-tight">Incident Investigation</h1>
      </div>

      <form onSubmit={submit} className="card p-4 flex gap-2 items-end" data-testid="ip-search-form">
        <label className="flex-1">
          <span className="font-mono text-[9px] tracking-[0.25em] uppercase text-slate-500 mb-1 block">Target IP address</span>
          <input value={ip} onChange={(e) => setIp(e.target.value)} placeholder="e.g. 185.220.101.42"
            data-testid="investigation-ip-input" className="input font-mono" />
        </label>
        <button type="submit" disabled={loading} data-testid="investigation-search"
          className="flex items-center gap-2 px-4 py-2 text-xs font-mono uppercase tracking-widest bg-blue-500 hover:bg-blue-400 text-black rounded-sm font-bold disabled:opacity-50">
          <MagnifyingGlass size={14}/> Analyze
        </button>
      </form>

      {data && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4" data-testid="investigation-summary">
            <Stat label="Target IP" value={data.ip} mono />
            <Stat label="Location" value={data.geo?.country ? `${data.geo?.city || "—"}, ${data.geo.country}` : "Unknown"} icon={MapPin} />
            <Stat label="Failed Logins" value={failures} severity={failures > 20 ? "critical" : failures > 5 ? "high" : "neutral"} />
            <Stat label="Unique Users" value={uniqueUsers} severity={uniqueUsers > 5 ? "high" : "neutral"} />
          </div>

          <div className="card p-5" data-testid="investigation-timeline">
            <div className="section-label mb-3">Login Timeline</div>
            <div className="h-48">
              {timeline.length > 0 ? (
                <ResponsiveContainer>
                  <LineChart data={timeline}>
                    <CartesianGrid stroke="#1F2937" strokeDasharray="2 4" />
                    <XAxis dataKey="ts" tick={{ fill: "#6B7280", fontSize: 10, fontFamily: "JetBrains Mono" }} />
                    <YAxis ticks={[0, 1]} tick={{ fill: "#6B7280", fontSize: 10, fontFamily: "JetBrains Mono" }} domain={[0, 1]} tickFormatter={(v) => v === 1 ? "OK" : "FAIL"} />
                    <Tooltip contentStyle={{ background: "#000", border: "1px solid #1F2937", borderRadius: 2 }} formatter={(v, n, p) => p?.payload?.label} />
                    <Line type="stepAfter" dataKey="status" stroke="#3B82F6" strokeWidth={1.5} dot={{ r: 2 }} />
                  </LineChart>
                </ResponsiveContainer>
              ) : <div className="h-full flex items-center justify-center text-xs text-slate-500 font-mono">No events</div>}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="card p-5" data-testid="investigation-events">
              <div className="section-label mb-3">Related Events</div>
              <div className="space-y-1.5 max-h-80 overflow-y-auto pr-2">
                {(data.items || []).map((it) => (
                  <div key={it.id} className="grid grid-cols-12 gap-2 items-center text-xs border-l-2 pl-2 py-1"
                    style={{ borderColor: it.status === "failure" ? "#EF4444" : "#10B981" }}>
                    <span className="col-span-4 font-mono text-slate-400">{(it.timestamp || "").slice(0, 19).replace("T", " ")}</span>
                    <span className="col-span-3 text-slate-200">{it.username}</span>
                    <span className="col-span-3 font-mono text-[10px] text-slate-400 uppercase">{it.event_type}</span>
                    <span className={`col-span-2 font-mono text-[10px] uppercase ${it.status === "failure" ? "text-red-400" : "text-emerald-400"}`}>{it.status}</span>
                  </div>
                ))}
                {(data.items || []).length === 0 && <div className="text-xs text-slate-500 font-mono">No events for this IP.</div>}
              </div>
            </div>

            <div className="card p-5" data-testid="investigation-alerts">
              <div className="section-label mb-3">Related Alerts</div>
              <div className="space-y-2 max-h-80 overflow-y-auto pr-2">
                {alerts.length === 0 && <div className="text-xs text-slate-500 font-mono">No alerts.</div>}
                {alerts.map((a) => (
                  <div key={a.id} className="border-l-2 pl-3 py-1"
                    style={{ borderColor: ({critical:"#EF4444",high:"#F59E0B",medium:"#3B82F6",low:"#10B981"}[a.severity] || "#3B82F6") }}>
                    <div className="flex items-center gap-2 mb-0.5">
                      <SeverityBadge severity={a.severity} />
                      {a.mitre_id && <span className="font-mono text-[10px] text-blue-400">{a.mitre_id}</span>}
                    </div>
                    <div className="text-xs text-slate-300">{a.message}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}

      {!data && !loading && (
        <div className="card p-12 text-center" data-testid="investigation-empty">
          <Lightning size={28} weight="duotone" className="text-slate-700 mx-auto mb-3" />
          <div className="font-mono text-xs uppercase tracking-widest text-slate-500">Enter an IP to begin forensic analysis</div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, icon: Icon, mono, severity = "neutral" }) {
  const colors = {
    critical: "text-red-300 border-red-900",
    high: "text-amber-300 border-amber-900",
    neutral: "text-slate-100 border-slate-800",
  };
  return (
    <div className={`card p-4 border ${colors[severity] || colors.neutral}`}>
      <div className="flex items-center gap-2">
        {Icon && <Icon size={14} className="text-blue-400" />}
        <div className="section-label">{label}</div>
      </div>
      <div className={`mt-2 ${mono ? "font-mono" : ""} text-xl font-bold tracking-tight`}>{value}</div>
    </div>
  );
}
