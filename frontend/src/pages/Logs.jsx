import React, { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { UploadSimple, Trash, FunnelSimple, MagnifyingGlass } from "@phosphor-icons/react";
import { api, apiError } from "../lib/api";
import { useNavigate } from "react-router-dom";

const EVENTS = ["", "login", "logout", "failed_login", "password_reset"];
const STATUS = ["", "success", "failure"];

export default function Logs() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);
  const [filters, setFilters] = useState({ event_type: "", status: "", ip: "", username: "", start: "", end: "" });
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef(null);
  const navigate = useNavigate();

  const load = async () => {
    try {
      const params = { page, page_size: pageSize };
      Object.entries(filters).forEach(([k, v]) => { if (v) params[k] = v; });
      const { data } = await api.get("/logs", { params });
      setItems(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      toast.error(apiError(err));
    }
  };

  useEffect(() => { load(); }, [page, filters]);

  const onFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const { data } = await api.post("/logs/upload", form, { headers: { "Content-Type": "multipart/form-data" }});
      toast.success(`Ingested ${data.inserted} entries. ${data.alerts_created} alerts.`);
      setPage(1);
      load();
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const clearAll = async () => {
    if (!window.confirm("Delete all your logs and alerts?")) return;
    try {
      await api.delete("/logs");
      toast.success("Cleared.");
      load();
    } catch (err) {
      toast.error(apiError(err));
    }
  };

  const downloadCsv = async () => {
    try {
      const res = await api.get("/reports/csv/logs", { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a"); a.href = url; a.download = "logs.csv"; a.click();
      URL.revokeObjectURL(url);
    } catch (err) { toast.error(apiError(err)); }
  };

  const pages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="space-y-5 anim-fade" data-testid="logs-page">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="section-label">// Telemetry</div>
          <h1 className="font-mono text-3xl font-bold tracking-tight">Log Entries</h1>
        </div>
        <div className="flex gap-2">
          <input ref={fileRef} type="file" accept=".csv,.json,.txt,.log" onChange={onFile} className="hidden" data-testid="file-input" />
          <button onClick={() => fileRef.current?.click()} disabled={uploading} data-testid="upload-btn"
            className="flex items-center gap-2 px-4 py-2 text-xs font-mono uppercase tracking-widest bg-blue-500 hover:bg-blue-400 text-black rounded-sm font-bold disabled:opacity-50">
            <UploadSimple size={14} /> {uploading ? "Uploading…" : "Upload Logs"}
          </button>
          <button onClick={downloadCsv} data-testid="export-csv-btn"
            className="px-4 py-2 text-xs font-mono uppercase tracking-widest border border-slate-800 hover:border-blue-500 hover:text-blue-300 text-slate-300 rounded-sm">
            Export CSV
          </button>
          <button onClick={clearAll} data-testid="clear-btn"
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-mono uppercase tracking-widest border border-slate-800 hover:border-red-500 hover:text-red-300 text-slate-400 rounded-sm">
            <Trash size={12} /> Clear
          </button>
        </div>
      </div>

      <div className="card p-3" data-testid="upload-help">
        <div className="text-xs text-slate-400">
          Accepted formats: <span className="font-mono text-slate-200">CSV, JSON, TXT</span>. Required columns/keys:
          <span className="font-mono text-blue-300"> timestamp, ip / ip_address, username, event_type, status</span>. Max 10 MB.
        </div>
      </div>

      {/* Filters */}
      <div className="card p-4" data-testid="logs-filters">
        <div className="flex items-center gap-2 mb-3">
          <FunnelSimple size={14} className="text-blue-400" />
          <div className="section-label">Filters</div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
          <Select label="Event type" value={filters.event_type} options={EVENTS} onChange={(v) => setFilters({ ...filters, event_type: v })} testid="filter-event" />
          <Select label="Status" value={filters.status} options={STATUS} onChange={(v) => setFilters({ ...filters, status: v })} testid="filter-status" />
          <SearchField label="IP address" value={filters.ip} onChange={(v) => setFilters({ ...filters, ip: v })} testid="filter-ip" placeholder="10.0.0.x" />
          <SearchField label="Username" value={filters.username} onChange={(v) => setFilters({ ...filters, username: v })} testid="filter-username" placeholder="alice" />
          <DateField label="From" value={filters.start} onChange={(v) => setFilters({ ...filters, start: v })} testid="filter-start" />
          <DateField label="To" value={filters.end} onChange={(v) => setFilters({ ...filters, end: v })} testid="filter-end" />
        </div>
      </div>

      {/* Table */}
      <div className="card" data-testid="logs-table-card">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-[#070708] border-b border-slate-800">
              <tr className="font-mono uppercase tracking-widest text-[10px] text-slate-500">
                {["Timestamp","IP","Username","Event","Status",""].map((h) => (
                  <th key={h} className="text-left px-4 py-2.5">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-500 font-mono text-xs">No logs match your filters.</td></tr>
              )}
              {items.map((l) => (
                <tr key={l.id} className="border-b border-slate-900/80 hover:bg-slate-900/30 transition-colors duration-100">
                  <td className="px-4 py-2 font-mono text-slate-300">{(l.timestamp || "").replace("T", " ").slice(0, 19)}</td>
                  <td className="px-4 py-2 font-mono text-blue-300">
                    <button className="hover:underline" onClick={() => navigate(`/investigation/${l.ip_address}`)} data-testid={`log-ip-${l.ip_address}`}>
                      {l.ip_address}
                    </button>
                  </td>
                  <td className="px-4 py-2 text-slate-200">{l.username}</td>
                  <td className="px-4 py-2 font-mono text-slate-400">{l.event_type}</td>
                  <td className="px-4 py-2">
                    <span className={`font-mono text-[10px] uppercase tracking-widest px-1.5 py-0.5 rounded-sm border ${
                      l.status === "success" ? "text-emerald-300 border-emerald-900 bg-emerald-500/5" : "text-red-300 border-red-900 bg-red-500/5"
                    }`}>{l.status}</span>
                  </td>
                  <td className="px-4 py-2 text-right">
                    <button onClick={() => navigate(`/investigation/${l.ip_address}`)} className="text-blue-400 hover:text-blue-300 font-mono text-[10px] uppercase tracking-widest flex items-center gap-1 ml-auto" data-testid={`investigate-${l.id}`}>
                      <MagnifyingGlass size={11}/>Investigate
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex items-center justify-between px-4 py-3 border-t border-slate-800 text-xs font-mono text-slate-400">
          <div>Showing <span className="text-slate-100">{items.length}</span> of <span className="text-slate-100">{total}</span></div>
          <div className="flex items-center gap-2">
            <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="px-3 py-1 border border-slate-800 hover:border-blue-500 rounded-sm disabled:opacity-30" data-testid="page-prev">Prev</button>
            <span className="text-slate-300">{page} / {pages}</span>
            <button disabled={page >= pages} onClick={() => setPage(page + 1)} className="px-3 py-1 border border-slate-800 hover:border-blue-500 rounded-sm disabled:opacity-30" data-testid="page-next">Next</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Select({ label, value, options, onChange, testid }) {
  return (
    <label className="block">
      <span className="font-mono text-[9px] tracking-[0.25em] uppercase text-slate-500 mb-1 block">{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)} data-testid={testid}
        className="input text-xs h-[34px]">
        {options.map((o) => <option key={o} value={o}>{o || "Any"}</option>)}
      </select>
    </label>
  );
}
function SearchField({ label, value, onChange, testid, placeholder }) {
  return (
    <label className="block">
      <span className="font-mono text-[9px] tracking-[0.25em] uppercase text-slate-500 mb-1 block">{label}</span>
      <input value={value} onChange={(e) => onChange(e.target.value)} data-testid={testid}
        placeholder={placeholder} className="input text-xs h-[34px]" />
    </label>
  );
}
function DateField({ label, value, onChange, testid }) {
  return (
    <label className="block">
      <span className="font-mono text-[9px] tracking-[0.25em] uppercase text-slate-500 mb-1 block">{label}</span>
      <input type="datetime-local" value={value} onChange={(e) => onChange(e.target.value)} data-testid={testid}
        className="input text-xs h-[34px] font-mono" />
    </label>
  );
}
