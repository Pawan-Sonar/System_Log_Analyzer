import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";
import { toast } from "sonner";
import { FileText, ShieldWarning, Globe, Warning, Skull, Lightning } from "@phosphor-icons/react";
import { api, apiError } from "../lib/api";
import KPICard from "../components/KPICard";
import RiskGauge from "../components/RiskGauge";
import SeverityBadge from "../components/SeverityBadge";

const EVENT_COLORS = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"];

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const [d, a] = await Promise.all([
        api.get("/analytics/dashboard"),
        api.get("/alerts?limit=20"),
      ]);
      setData(d.data);
      setAlerts(a.data.items || []);
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const seedDemo = async () => {
    try {
      await api.post("/logs/seed-demo");
      toast.success("Demo dataset injected.");
      load();
    } catch (err) {
      toast.error(apiError(err));
    }
  };

  const kpi = data?.kpi || { total_logs: 0, failed_logins: 0, suspicious_ips: 0, risk_score: 0, risk_level: "low" };
  const sevForRisk = kpi.risk_level || "low";
  const hasData = (data?.kpi?.total_logs || 0) > 0;

  return (
    <div className="space-y-6 anim-fade" data-testid="dashboard">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="section-label">// Operations</div>
          <h1 className="font-mono text-3xl font-bold tracking-tight">Threat Dashboard</h1>
        </div>
        <div className="flex gap-2">
          <button onClick={seedDemo} data-testid="seed-demo-btn"
            className="px-4 py-2 text-xs font-mono uppercase tracking-widest border border-slate-800 hover:border-blue-500 hover:text-blue-300 text-slate-300 rounded-sm transition-all duration-150">
            Inject Demo Data
          </button>
          <button onClick={() => navigate("/logs")} data-testid="upload-link-btn"
            className="px-4 py-2 text-xs font-mono uppercase tracking-widest bg-blue-500 hover:bg-blue-400 text-black rounded-sm font-bold transition-all duration-150">
            Upload Logs →
          </button>
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KPICard testid="kpi-total-logs" label="Total Log Entries" value={kpi.total_logs.toLocaleString()} hint="Entries ingested" icon={FileText} severity="medium" />
        <KPICard testid="kpi-failed-logins" label="Failed Logins" value={kpi.failed_logins.toLocaleString()} hint="Authentication failures" icon={Warning} severity={kpi.failed_logins > 20 ? "high" : "neutral"} />
        <KPICard testid="kpi-suspicious-ips" label="Suspicious IPs" value={kpi.suspicious_ips} hint="Flagged sources" icon={Globe} severity={kpi.suspicious_ips > 0 ? "high" : "neutral"} />
        <KPICard testid="kpi-risk-score" label="Risk Score" value={`${kpi.risk_score}/100`} hint={`${(kpi.risk_level||"low").toUpperCase()} risk`} icon={ShieldWarning} severity={sevForRisk} />
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Risk gauge */}
        <div className="card p-5 lg:col-span-1" data-testid="risk-gauge-card">
          <div className="section-label mb-2">Risk Posture</div>
          <RiskGauge score={kpi.risk_score} level={sevForRisk} />
          <div className="mt-2 grid grid-cols-2 gap-2 text-center">
            <Pill color="#10B981" label="LOW" value="0–24" />
            <Pill color="#3B82F6" label="MED" value="25–49" />
            <Pill color="#F59E0B" label="HIGH" value="50–74" />
            <Pill color="#EF4444" label="CRIT" value="75–100" />
          </div>
        </div>

        {/* Time series */}
        <div className="card p-5 lg:col-span-3" data-testid="chart-attack-trend">
          <div className="flex justify-between items-center mb-3">
            <div>
              <div className="section-label">Attack Trend Timeline</div>
              <div className="text-xs text-slate-500 mt-0.5">Hourly success vs failure</div>
            </div>
            <div className="flex gap-3 text-[10px] font-mono uppercase tracking-widest">
              <span className="flex items-center gap-1.5"><span className="w-2 h-2 bg-emerald-500"/>Success</span>
              <span className="flex items-center gap-1.5"><span className="w-2 h-2 bg-red-500"/>Failure</span>
            </div>
          </div>
          <div className="h-64">
            {hasData ? (
              <ResponsiveContainer>
                <AreaChart data={data.timeseries}>
                  <defs>
                    <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#10B981" stopOpacity={0.4}/>
                      <stop offset="100%" stopColor="#10B981" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#EF4444" stopOpacity={0.4}/>
                      <stop offset="100%" stopColor="#EF4444" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="#1F2937" strokeDasharray="2 4" />
                  <XAxis dataKey="bucket" tick={{ fill: "#6B7280", fontSize: 10, fontFamily: "JetBrains Mono" }} tickFormatter={(v) => v.slice(11, 16)} />
                  <YAxis tick={{ fill: "#6B7280", fontSize: 10, fontFamily: "JetBrains Mono" }} />
                  <Tooltip contentStyle={{ background: "#000", border: "1px solid #1F2937", borderRadius: 2, fontFamily: "JetBrains Mono", fontSize: 11 }} />
                  <Area type="monotone" dataKey="success" stroke="#10B981" fill="url(#g1)" strokeWidth={1.5} />
                  <Area type="monotone" dataKey="failure" stroke="#EF4444" fill="url(#g2)" strokeWidth={1.5} />
                </AreaChart>
              </ResponsiveContainer>
            ) : <EmptyChart />}
          </div>
        </div>

        {/* Login Success vs Failure */}
        <div className="card p-5 lg:col-span-2" data-testid="chart-success-failure">
          <div className="section-label mb-3">Login Success vs Failure</div>
          <div className="h-56">
            {hasData ? (
              <ResponsiveContainer>
                <BarChart data={[
                  { name: "Success", value: kpi.success_logins || 0, fill: "#10B981" },
                  { name: "Failure", value: kpi.failed_logins || 0, fill: "#EF4444" },
                ]}>
                  <CartesianGrid stroke="#1F2937" strokeDasharray="2 4" />
                  <XAxis dataKey="name" tick={{ fill: "#9CA3AF", fontSize: 11, fontFamily: "JetBrains Mono" }} />
                  <YAxis tick={{ fill: "#6B7280", fontSize: 10, fontFamily: "JetBrains Mono" }} />
                  <Tooltip cursor={{ fill: "rgba(59,130,246,0.05)" }} contentStyle={{ background: "#000", border: "1px solid #1F2937", borderRadius: 2 }} />
                  <Bar dataKey="value" />
                </BarChart>
              </ResponsiveContainer>
            ) : <EmptyChart />}
          </div>
        </div>

        {/* Top suspicious IPs */}
        <div className="card p-5 lg:col-span-2" data-testid="chart-top-ips">
          <div className="section-label mb-3">Top Suspicious IPs</div>
          <div className="h-56">
            {(data?.top_suspicious_ips?.length || 0) > 0 ? (
              <ResponsiveContainer>
                <BarChart data={(data.top_suspicious_ips || []).slice(0, 6)} layout="vertical" margin={{ left: 24 }}>
                  <CartesianGrid stroke="#1F2937" strokeDasharray="2 4" />
                  <XAxis type="number" tick={{ fill: "#6B7280", fontSize: 10, fontFamily: "JetBrains Mono" }} />
                  <YAxis dataKey="ip" type="category" width={110} tick={{ fill: "#9CA3AF", fontSize: 10, fontFamily: "JetBrains Mono" }} />
                  <Tooltip contentStyle={{ background: "#000", border: "1px solid #1F2937", borderRadius: 2 }} />
                  <Bar dataKey="count" fill="#EF4444" onClick={(d) => d?.ip && navigate(`/investigation/${d.ip}`)} cursor="pointer" />
                </BarChart>
              </ResponsiveContainer>
            ) : <EmptyChart />}
          </div>
        </div>

        {/* Event distribution */}
        <div className="card p-5 lg:col-span-2" data-testid="chart-event-distribution">
          <div className="section-label mb-3">Event Distribution by Type</div>
          <div className="h-56">
            {(data?.event_distribution?.length || 0) > 0 ? (
              <ResponsiveContainer>
                <PieChart>
                  <Pie data={data.event_distribution} dataKey="count" nameKey="event_type" outerRadius={80} innerRadius={50}>
                    {data.event_distribution.map((_, i) => <Cell key={i} fill={EVENT_COLORS[i % EVENT_COLORS.length]} stroke="#0A0A0A" />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#000", border: "1px solid #1F2937", borderRadius: 2, fontFamily: "JetBrains Mono", fontSize: 11 }} />
                </PieChart>
              </ResponsiveContainer>
            ) : <EmptyChart />}
          </div>
          <div className="mt-2 flex flex-wrap gap-2 text-[10px] font-mono uppercase tracking-wider">
            {(data?.event_distribution || []).map((d, i) => (
              <span key={d.event_type} className="flex items-center gap-1.5 text-slate-400">
                <span className="w-2 h-2 inline-block" style={{ background: EVENT_COLORS[i % EVENT_COLORS.length] }} />
                {d.event_type} <span className="text-slate-500">({d.count})</span>
              </span>
            ))}
          </div>
        </div>

        {/* Alerts feed */}
        <div className="card p-5 lg:col-span-2" data-testid="alerts-feed-card">
          <div className="flex items-center justify-between mb-3">
            <div className="section-label flex items-center gap-2">
              <Skull size={12} className="text-red-400" /> Live Alerts
              <span className="w-1.5 h-1.5 bg-red-500 rounded-full pulse-dot" />
            </div>
            <button onClick={() => navigate("/alerts")} className="text-[10px] font-mono uppercase tracking-widest text-blue-400 hover:text-blue-300">
              View all →
            </button>
          </div>
          <div className="space-y-2 max-h-56 overflow-y-auto pr-2" data-testid="alerts-feed-list">
            {alerts.length === 0 && <div className="text-xs text-slate-500 font-mono">No alerts. System nominal.</div>}
            {alerts.map((a) => (
              <div key={a.id} className="anim-fade border-l-2 pl-3 py-1.5"
                style={{ borderColor: ({critical:"#EF4444",high:"#F59E0B",medium:"#3B82F6",low:"#10B981"}[a.severity] || "#3B82F6") }}>
                <div className="flex items-center gap-2 mb-0.5">
                  <SeverityBadge severity={a.severity} />
                  <span className="font-mono text-[10px] text-slate-500">{a.type}</span>
                  {a.mitre_id && <span className="font-mono text-[10px] text-blue-400">{a.mitre_id}</span>}
                </div>
                <div className="text-xs text-slate-300">{a.message}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function Pill({ color, label, value }) {
  return (
    <div className="border border-slate-800 px-2 py-1 rounded-sm">
      <div className="font-mono text-[9px] tracking-widest" style={{ color }}>{label}</div>
      <div className="font-mono text-[10px] text-slate-400">{value}</div>
    </div>
  );
}

function EmptyChart() {
  return (
    <div className="h-full flex items-center justify-center text-xs font-mono uppercase tracking-widest text-slate-600 gap-2">
      <Lightning size={14} /> No data — upload logs or inject demo
    </div>
  );
}
