import { useState, useEffect, useCallback, useRef } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area } from "recharts";

// ── CONFIG ────────────────────────────────────────────────────────────────────
const API = "http://localhost:8080/api";
const POLL_MS = 30000; // refresh every 30s

// ── HELPERS ───────────────────────────────────────────────────────────────────
const fmt = (n, dec = 1) => n == null ? "—" : Number(n).toFixed(dec);
const fmtMem = (mb) => mb == null ? "—" : mb >= 1024 ? `${(mb/1024).toFixed(1)} GB` : `${Math.round(mb)} MB`;
const ago = (iso) => {
  if (!iso) return "—";
  const diff = (Date.now() - new Date(iso)) / 1000;
  if (diff < 60) return `${Math.round(diff)}s ago`;
  if (diff < 3600) return `${Math.round(diff/60)}m ago`;
  return `${Math.round(diff/3600)}h ago`;
};

const STATUS_COLOR = { ok: "#00e5a0", warn: "#ffd32a", error: "#ff4757", unknown: "#7a8aac" };
const SYNC_COLOR = { SYNCHRONIZED: "#00e5a0", SYNCHRONIZING: "#ffd32a", "NOT SYNCHRONIZING": "#ff4757" };

// ── API CALLS ─────────────────────────────────────────────────────────────────
const api = {
  servers: () => fetch(`${API}/servers`).then(r => r.json()),
  health: (id) => fetch(`${API}/metrics/${id}/health`).then(r => r.json()),
  history: (id) => fetch(`${API}/metrics/${id}/history?hours=4`).then(r => r.json()),
  sessions: (id) => fetch(`${API}/metrics/${id}/sessions`).then(r => r.json()),
  waits: (id) => fetch(`${API}/metrics/${id}/waits`).then(r => r.json()),
  ag: (id) => fetch(`${API}/clusters/${id}/ag/summary`).then(r => r.json()),
  fci: (id) => fetch(`${API}/clusters/${id}/fci`).then(r => r.json()),
  logship: (id) => fetch(`${API}/clusters/${id}/logshipping`).then(r => r.json()),
  alerts: () => fetch(`${API}/alerts/events?hours=24`).then(r => r.json()),
  unacked: () => fetch(`${API}/alerts/unacked-count`).then(r => r.json()),
  testConn: (id) => fetch(`${API}/servers/${id}/test`, { method: "POST" }).then(r => r.json()),
  createServer: (data) => fetch(`${API}/servers`, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(data) }).then(r => r.json()),
  deleteServer: (id) => fetch(`${API}/servers/${id}`, { method: "DELETE" }),
};

// ── NEW: IMPORT BUTTON COMPONENT ───────────────────────────────────────────────
function ImportServerButton({ onImportSuccess, style }) {
  const fileInputRef = useRef(null);
  const [isUploading, setIsUploading] = useState(false);

  const handleButtonClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setIsUploading(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API}/servers/import`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Failed to import servers');
      }

      const data = await response.json();
      alert(data.message); 
      
      if (onImportSuccess) {
        onImportSuccess();
      }
    } catch (error) {
      console.error('Error importing file:', error);
      alert('There was an error importing the file. Please check the format.');
    } finally {
      setIsUploading(false);
      event.target.value = null; 
    }
  };

  return (
    <>
      <button 
        onClick={handleButtonClick} 
        disabled={isUploading}
        style={{
          background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)",
          color: "#f0f4ff", borderRadius: 8, padding: "6px 14px", cursor: isUploading ? "wait" : "pointer",
          fontFamily: "'DM Mono', monospace", fontSize: 11, fontWeight: 600, transition: "background 0.2s",
          ...style
        }}
      >
        {isUploading ? 'Importing...' : '📥 Import from SSMS'}
      </button>

      <input
        type="file"
        accept=".regsrvr,.xml"
        ref={fileInputRef}
        style={{ display: 'none' }}
        onChange={handleFileChange}
      />
    </>
  );
}

// ── WINDOW CONTROLS ───────────────────────────────────────────────────────────
function WindowControls() {
  const btnStyle = {
    background: "transparent", border: "none", color: "#7a8aac",
    width: 46, height: 52, display: "flex", alignItems: "center", justifyContent: "center",
    cursor: "pointer", transition: "background 0.2s", WebkitAppRegion: "no-drag"
  };

  // Safely trigger the functions you exposed in preload.js
  const handleMinimize = () => window.electronAPI?.minimize();
  const handleMaximize = () => window.electronAPI?.maximize();
  const handleClose = () => window.electronAPI?.close();

  return (
    <div style={{ display: "flex", WebkitAppRegion: "no-drag", marginLeft: 16 }}>
      <button 
        style={btnStyle} 
        onMouseEnter={e => e.currentTarget.style.background="rgba(255,255,255,0.1)"} 
        onMouseLeave={e => e.currentTarget.style.background="transparent"} 
        onClick={handleMinimize}
      >
        <svg width="12" height="12" viewBox="0 0 12 12"><rect fill="currentColor" width="10" height="1" x="1" y="6"></rect></svg>
      </button>
      <button 
        style={btnStyle} 
        onMouseEnter={e => e.currentTarget.style.background="rgba(255,255,255,0.1)"} 
        onMouseLeave={e => e.currentTarget.style.background="transparent"} 
        onClick={handleMaximize}
      >
        <svg width="12" height="12" viewBox="0 0 12 12"><rect width="9" height="9" x="1.5" y="1.5" fill="none" stroke="currentColor"></rect></svg>
      </button>
      <button 
        style={{...btnStyle, transition: "background 0.2s, color 0.2s"}} 
        onMouseEnter={e => {e.currentTarget.style.background="#e81123"; e.currentTarget.style.color="#fff"}} 
        onMouseLeave={e => {e.currentTarget.style.background="transparent"; e.currentTarget.style.color="#7a8aac"}} 
        onClick={handleClose}
      >
        <svg width="12" height="12" viewBox="0 0 12 12"><polygon fill="currentColor" fillRule="evenodd" points="11 1.576 6.583 6 11 10.424 10.424 11 6 6.583 1.576 11 1 10.424 5.417 6 1 1.576 1.576 1 6 5.417 10.424 1"></polygon></svg>
      </button>
    </div>
  );
}

// ── PULSE DOT ─────────────────────────────────────────────────────────────────
function Pulse({ color = "#00e5a0", size = 8 }) {
  return (
    <span style={{ position:"relative", display:"inline-flex", alignItems:"center", justifyContent:"center", width: size+8, height: size+8 }}>
      <span style={{
        position:"absolute", width: size+6, height: size+6, borderRadius:"50%",
        background: color, opacity: 0.25,
        animation: "pulseRing 2s ease infinite"
      }}/>
      <span style={{ width: size, height: size, borderRadius:"50%", background: color, display:"block" }}/>
    </span>
  );
}

// ── STAT CARD ─────────────────────────────────────────────────────────────────
function StatCard({ label, value, unit, color, sub, chart }) {
  return (
    <div style={{
      background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)",
      borderRadius: 10, padding: "14px 16px", flex: 1, minWidth: 0,
      borderTop: `2px solid ${color || "rgba(255,255,255,0.1)"}`,
      transition: "border-color 0.3s"
    }}>
      <div style={{ fontSize: 10, fontFamily: "'DM Mono', monospace", color: "#7a8aac", textTransform:"uppercase", letterSpacing:"0.1em", marginBottom: 6 }}>{label}</div>
      <div style={{ display:"flex", alignItems:"baseline", gap: 4 }}>
        <span style={{ fontFamily:"'Syne', sans-serif", fontSize: 28, fontWeight: 800, color: color || "#f0f4ff", lineHeight: 1 }}>{value}</span>
        {unit && <span style={{ fontSize: 11, color: "#7a8aac", fontFamily:"'DM Mono', monospace" }}>{unit}</span>}
      </div>
      {sub && <div style={{ fontSize: 11, color: "#7a8aac", marginTop: 4 }}>{sub}</div>}
      {chart && chart.length > 1 && (
        <div style={{ marginTop: 8, height: 32 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chart} margin={{top:0,right:0,bottom:0,left:0}}>
              <Area type="monotone" dataKey="v" stroke={color || "#1a6cf5"} fill={`${color || "#1a6cf5"}22`} strokeWidth={1.5} dot={false} isAnimationActive={false}/>
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

// ── SECTION HEADER ────────────────────────────────────────────────────────────
function SectionHeader({ label, icon, action }) {
  return (
    <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom: 12 }}>
      <div style={{ display:"flex", alignItems:"center", gap: 8 }}>
        <span style={{ fontSize: 14 }}>{icon}</span>
        <span style={{ fontFamily:"'DM Mono', monospace", fontSize: 11, letterSpacing:"0.12em", textTransform:"uppercase", color:"#7a8aac" }}>{label}</span>
      </div>
      {action}
    </div>
  );
}

// ── BADGE ─────────────────────────────────────────────────────────────────────
function Badge({ text, color }) {
  const c = color || "#7a8aac";
  return (
    <span style={{
      padding: "2px 8px", borderRadius: 4, fontSize: 10,
      fontFamily:"'DM Mono', monospace", fontWeight: 600, letterSpacing:"0.05em",
      background: `${c}18`, color: c, border: `1px solid ${c}30`
    }}>{text}</span>
  );
}

// ── WAIT BARS ─────────────────────────────────────────────────────────────────
function WaitBars({ waits }) {
  if (!waits?.length) return <div style={{ color:"#7a8aac", fontSize: 12, textAlign:"center", padding: "20px 0" }}>No significant waits</div>;
  const max = Math.max(...waits.map(w => w.wait_time_ms || 0));
  return (
    <div style={{ display:"flex", flexDirection:"column", gap: 6 }}>
      {waits.slice(0,8).map((w, i) => (
        <div key={i}>
          <div style={{ display:"flex", justifyContent:"space-between", marginBottom: 3 }}>
            <span style={{ fontFamily:"'DM Mono', monospace", fontSize: 10, color:"#c0cce0" }}>{w.wait_type}</span>
            <span style={{ fontFamily:"'DM Mono', monospace", fontSize: 10, color:"#7a8aac" }}>{((w.wait_time_ms||0)/1000).toFixed(1)}s</span>
          </div>
          <div style={{ height: 4, background:"rgba(255,255,255,0.06)", borderRadius: 2, overflow:"hidden" }}>
            <div style={{
              height:"100%", borderRadius: 2,
              width: `${max > 0 ? (w.wait_time_ms/max)*100 : 0}%`,
              background: i === 0 ? "#ff4757" : i < 3 ? "#ffd32a" : "#1a6cf5",
              transition: "width 0.5s ease"
            }}/>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── AG PANEL ──────────────────────────────────────────────────────────────────
function AGPanel({ data }) {
  if (!data?.has_ag) return <div style={{ color:"#7a8aac", fontSize: 12, textAlign:"center", padding: "20px 0" }}>No Availability Groups detected</div>;
  return (
    <div style={{ display:"flex", flexDirection:"column", gap: 8 }}>
      {data.groups?.map((g, gi) => (
        <div key={gi} style={{ background:"rgba(255,255,255,0.02)", border:"1px solid rgba(255,255,255,0.06)", borderRadius: 8, padding: 12 }}>
          <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom: 8 }}>
            <span style={{ fontFamily:"'Syne', sans-serif", fontWeight: 700, fontSize: 13 }}>{g.ag_name}</span>
            <div style={{ display:"flex", alignItems:"center", gap: 6 }}>
              <Pulse color={g.healthy ? "#00e5a0" : "#ff4757"} size={6}/>
              <span style={{ fontSize: 10, fontFamily:"'DM Mono', monospace", color: g.healthy ? "#00e5a0" : "#ff4757" }}>
                {g.healthy ? "HEALTHY" : "DEGRADED"}
              </span>
            </div>
          </div>
          {g.primary && <div style={{ fontSize: 11, color:"#7a8aac", marginBottom: 8 }}>Primary: <span style={{ color:"#00d4ff" }}>{g.primary}</span></div>}
          <div style={{ display:"flex", flexDirection:"column", gap: 4 }}>
            {g.replicas?.slice(0,6).map((r, ri) => (
              <div key={ri} style={{
                display:"grid", gridTemplateColumns:"1fr auto auto auto",
                gap: 8, alignItems:"center", padding:"6px 8px",
                background:"rgba(255,255,255,0.02)", borderRadius: 5, fontSize: 11
              }}>
                <span style={{ fontFamily:"'DM Mono', monospace", color:"#c0cce0", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{r.replica_server_name}</span>
                <Badge text={r.role || "—"} color={r.role === "PRIMARY" ? "#00d4ff" : "#7a8aac"}/>
                <Badge text={r.synchronization_state || r.sync_state || "—"} color={SYNC_COLOR[r.synchronization_state || r.sync_state] || "#7a8aac"}/>
                <span style={{ fontFamily:"'DM Mono', monospace", color:"#7a8aac", fontSize: 10, whiteSpace:"nowrap" }}>
                  {r.redo_queue_kb != null ? `${Math.round(r.redo_queue_kb)}KB` : "—"}
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── FCI PANEL ─────────────────────────────────────────────────────────────────
function FCIPanel({ data }) {
  if (!data?.is_clustered) return <div style={{ color:"#7a8aac", fontSize: 12, textAlign:"center", padding: "20px 0" }}>Not a clustered instance</div>;
  return (
    <div>
      <div style={{ marginBottom: 10, display:"flex", alignItems:"center", gap: 8 }}>
        <span style={{ fontSize: 11, color:"#7a8aac", fontFamily:"'DM Mono', monospace" }}>ACTIVE NODE</span>
        <span style={{ fontFamily:"'Syne', sans-serif", fontWeight: 700, color:"#00d4ff" }}>{data.active_node || "Unknown"}</span>
      </div>
      <div style={{ display:"flex", flexDirection:"column", gap: 4 }}>
        {data.nodes?.map((n, i) => (
          <div key={i} style={{
            display:"flex", alignItems:"center", justifyContent:"space-between",
            padding:"8px 10px", background: n.is_current_owner ? "rgba(0,212,255,0.06)" : "rgba(255,255,255,0.02)",
            border: `1px solid ${n.is_current_owner ? "rgba(0,212,255,0.2)" : "rgba(255,255,255,0.06)"}`,
            borderRadius: 6
          }}>
            <div style={{ display:"flex", alignItems:"center", gap: 8 }}>
              <Pulse color={n.status === 0 ? "#00e5a0" : "#ff4757"} size={6}/>
              <span style={{ fontFamily:"'DM Mono', monospace", fontSize: 12, color:"#c0cce0" }}>{n.NodeName}</span>
              {n.is_current_owner && <Badge text="ACTIVE" color="#00d4ff"/>}
            </div>
            <span style={{ fontSize: 10, fontFamily:"'DM Mono', monospace", color:"#7a8aac" }}>{n.status_description}</span>
          </div>
        ))}
      </div>
      {data.shared_drives?.length > 0 && (
        <div style={{ marginTop: 10 }}>
          <div style={{ fontSize: 10, fontFamily:"'DM Mono', monospace", color:"#7a8aac", marginBottom: 6, textTransform:"uppercase", letterSpacing:"0.1em" }}>Shared Drives</div>
          <div style={{ display:"flex", gap: 6, flexWrap:"wrap" }}>
            {data.shared_drives.map((d, i) => (
              <Badge key={i} text={`${d.DriveName} ${d.IsMounted ? "●" : "○"}`} color={d.IsMounted ? "#00e5a0" : "#ff4757"}/>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── LOG SHIPPING PANEL ────────────────────────────────────────────────────────
function LogShipPanel({ data }) {
  if (!data?.has_log_shipping) return <div style={{ color:"#7a8aac", fontSize: 12, textAlign:"center", padding: "20px 0" }}>No log shipping configured</div>;
  const rows = data.alerts || [];
  return (
    <div style={{ display:"flex", flexDirection:"column", gap: 4 }}>
      {rows.map((r, i) => {
        const status = r.backup_status === "critical" || r.restore_status === "critical" ? "critical"
          : r.backup_status === "warning" || r.restore_status === "warning" ? "warning" : "ok";
        const color = STATUS_COLOR[status];
        return (
          <div key={i} style={{
            padding:"10px 12px", background:"rgba(255,255,255,0.02)",
            border:`1px solid ${color}30`, borderLeft:`3px solid ${color}`,
            borderRadius: 6
          }}>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom: 6 }}>
              <span style={{ fontFamily:"'Syne', sans-serif", fontWeight: 700, fontSize: 12 }}>{r.primary_database}</span>
              <Badge text={status.toUpperCase()} color={color}/>
            </div>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap: 8, fontSize: 10, fontFamily:"'DM Mono', monospace", color:"#7a8aac" }}>
              <div>Backup<br/><span style={{ color: STATUS_COLOR[r.backup_status] }}>{r.minutes_since_backup != null ? `${r.minutes_since_backup}m ago` : "—"}</span></div>
              <div>Copy<br/><span style={{ color:"#c0cce0" }}>{ago(r.last_copy_date)}</span></div>
              <div>Restore<br/><span style={{ color: STATUS_COLOR[r.restore_status] }}>{r.minutes_since_restore != null ? `${r.minutes_since_restore}m ago` : "—"}</span></div>
            </div>
          </div>
        );
      })}
      {!rows.length && <div style={{ color:"#7a8aac", fontSize: 12, textAlign:"center", padding: "20px 0" }}>No databases configured</div>}
    </div>
  );
}

// ── BLOCKED SESSIONS ──────────────────────────────────────────────────────────
function BlockedPanel({ sessions }) {
  const blocked = sessions?.blocked_details || [];
  if (!blocked.length) return (
    <div style={{ display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", padding:"24px 0", gap: 8 }}>
      <span style={{ fontSize: 28 }}>✓</span>
      <span style={{ color:"#00e5a0", fontFamily:"'DM Mono', monospace", fontSize: 12 }}>No blocked sessions</span>
    </div>
  );
  return (
    <div style={{ display:"flex", flexDirection:"column", gap: 6 }}>
      {blocked.map((s, i) => (
        <div key={i} style={{ padding:"10px 12px", background:"rgba(255,71,87,0.05)", border:"1px solid rgba(255,71,87,0.2)", borderRadius: 6 }}>
          <div style={{ display:"flex", justifyContent:"space-between", marginBottom: 6 }}>
            <div style={{ display:"flex", gap: 8, alignItems:"center" }}>
              <Badge text={`SID ${s.session_id}`} color="#ff4757"/>
              <span style={{ fontSize: 10, color:"#7a8aac", fontFamily:"'DM Mono', monospace" }}>blocked by {s.blocking_session_id}</span>
            </div>
            <span style={{ fontSize: 10, fontFamily:"'DM Mono', monospace", color:"#ffd32a" }}>{fmt(s.wait_seconds, 1)}s</span>
          </div>
          <div style={{ fontFamily:"'DM Mono', monospace", fontSize: 10, color:"#7a8aac", marginBottom: 4 }}>{s.login_name} @ {s.host_name}</div>
          <div style={{
            fontFamily:"'DM Mono', monospace", fontSize: 10, color:"#c0cce0",
            background:"rgba(0,0,0,0.3)", padding:"4px 6px", borderRadius: 4,
            overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap"
          }}>{s.current_sql || "—"}</div>
        </div>
      ))}
    </div>
  );
}

// ── ADD SERVER MODAL ──────────────────────────────────────────────────────────
function AddServerModal({ onClose, onSaved }) {
  const [form, setForm] = useState({
    display_name:"", host:"", port:1433, instance_name:"",
    auth_type:"sql", username:"", password:"", cert_path:"",
    encrypt:false, trust_cert:true, role:"standalone",
    cluster_name:"", poll_interval:60, notes:""
  });
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [saving, setSaving] = useState(false);

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const saved = await api.createServer(form);
      const result = await api.testConn(saved.id);
      setTestResult(result);
      if (!result.success) await api.deleteServer(saved.id);
      else set("_saved_id", saved.id);
    } catch(e) { setTestResult({ success:false, error: e.message }); }
    setTesting(false);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (form._saved_id) { onSaved(); onClose(); }
      else { await api.createServer(form); onSaved(); onClose(); }
    } catch(e) { alert("Save failed: " + e.message); }
    setSaving(false);
  };

  const inp = { background:"rgba(0,0,0,0.3)", border:"1px solid rgba(255,255,255,0.1)", borderRadius:6, padding:"8px 10px", color:"#f0f4ff", fontFamily:"'DM Mono', monospace", fontSize:12, width:"100%", outline:"none" };
  const lbl = { fontSize:10, fontFamily:"'DM Mono', monospace", color:"#7a8aac", textTransform:"uppercase", letterSpacing:"0.1em", marginBottom:4, display:"block" };

  return (
    <div style={{ position:"fixed", inset:0, background:"rgba(0,0,0,0.7)", backdropFilter:"blur(8px)", zIndex:1000, display:"flex", alignItems:"center", justifyContent:"center", padding:16 }}>
      <div style={{ background:"#0d1428", border:"1px solid rgba(255,255,255,0.1)", borderRadius:14, padding:28, width:"100%", maxWidth:520, maxHeight:"90vh", overflowY:"auto" }}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:20 }}>
          <span style={{ fontFamily:"'Syne', sans-serif", fontWeight:800, fontSize:18 }}>Add Server</span>
          <button onClick={onClose} style={{ background:"none", border:"none", color:"#7a8aac", cursor:"pointer", fontSize:20 }}>✕</button>
        </div>

        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
          <div style={{ gridColumn:"1/-1" }}>
            <label style={lbl}>Display Name</label>
            <input style={inp} value={form.display_name} onChange={e=>set("display_name",e.target.value)} placeholder="My SQL Server"/>
          </div>
          <div>
            <label style={lbl}>Host / VNN / IP</label>
            <input style={inp} value={form.host} onChange={e=>set("host",e.target.value)} placeholder="SQLSERVER01"/>
          </div>
          <div>
            <label style={lbl}>Port</label>
            <input style={inp} type="number" value={form.port} onChange={e=>set("port",parseInt(e.target.value))}/>
          </div>
          <div>
            <label style={lbl}>Instance Name (optional)</label>
            <input style={inp} value={form.instance_name} onChange={e=>set("instance_name",e.target.value)} placeholder="MSSQLSERVER"/>
          </div>
          <div>
            <label style={lbl}>Auth Type</label>
            <select style={{...inp}} value={form.auth_type} onChange={e=>set("auth_type",e.target.value)}>
              <option value="sql">SQL Server Auth</option>
              <option value="windows">Windows Auth</option>
              <option value="tls_cert">TLS / Certificate</option>
            </select>
          </div>
          {form.auth_type !== "windows" && <>
            <div>
              <label style={lbl}>Username</label>
              <input style={inp} value={form.username} onChange={e=>set("username",e.target.value)} placeholder="sa"/>
            </div>
            <div>
              <label style={lbl}>Password</label>
              <input style={inp} type="password" value={form.password} onChange={e=>set("password",e.target.value)}/>
            </div>
          </>}
          {form.auth_type === "tls_cert" && (
            <div style={{ gridColumn:"1/-1" }}>
              <label style={lbl}>Certificate Path (.pem / .cer)</label>
              <input style={inp} value={form.cert_path} onChange={e=>set("cert_path",e.target.value)} placeholder="C:\certs\aws-rds-ca.pem"/>
            </div>
          )}
          <div>
            <label style={lbl}>Role</label>
            <select style={{...inp}} value={form.role} onChange={e=>set("role",e.target.value)}>
              <option value="standalone">Standalone</option>
              <option value="fci">FCI</option>
              <option value="ag_primary">AG Primary</option>
              <option value="ag_secondary">AG Secondary</option>
              <option value="log_primary">Log Ship Primary</option>
              <option value="log_secondary">Log Ship Secondary</option>
              <option value="log_monitor">Log Ship Monitor</option>
            </select>
          </div>
          <div>
            <label style={lbl}>Poll Interval (seconds)</label>
            <input style={inp} type="number" value={form.poll_interval} onChange={e=>set("poll_interval",parseInt(e.target.value))} min={10} max={3600}/>
          </div>
          <div style={{ gridColumn:"1/-1", display:"flex", gap:12 }}>
            <label style={{ display:"flex", alignItems:"center", gap:6, cursor:"pointer" }}>
              <input type="checkbox" checked={form.encrypt} onChange={e=>set("encrypt",e.target.checked)}/>
              <span style={{ fontSize:11, color:"#7a8aac", fontFamily:"'DM Mono', monospace" }}>Force TLS Encrypt</span>
            </label>
            <label style={{ display:"flex", alignItems:"center", gap:6, cursor:"pointer" }}>
              <input type="checkbox" checked={form.trust_cert} onChange={e=>set("trust_cert",e.target.checked)}/>
              <span style={{ fontSize:11, color:"#7a8aac", fontFamily:"'DM Mono', monospace" }}>Trust Server Certificate</span>
            </label>
          </div>
        </div>

        {testResult && (
          <div style={{
            marginTop:14, padding:"10px 12px", borderRadius:8,
            background: testResult.success ? "rgba(0,229,160,0.08)" : "rgba(255,71,87,0.08)",
            border: `1px solid ${testResult.success ? "rgba(0,229,160,0.2)" : "rgba(255,71,87,0.2)"}`,
            fontFamily:"'DM Mono', monospace", fontSize:11,
            color: testResult.success ? "#00e5a0" : "#ff4757"
          }}>
            {testResult.success ? `✓ Connected — ${testResult.server_name}` : `✗ ${testResult.error}`}
          </div>
        )}

        <div style={{ display:"flex", gap:10, marginTop:20 }}>
          <button onClick={handleTest} disabled={testing || !form.host} style={{
            flex:1, padding:"10px", borderRadius:8, border:"1px solid rgba(255,255,255,0.1)",
            background:"rgba(255,255,255,0.05)", color:"#f0f4ff", cursor:"pointer",
            fontFamily:"'DM Mono', monospace", fontSize:12, fontWeight:600
          }}>{testing ? "Testing…" : "Test Connection"}</button>
          <button onClick={handleSave} disabled={saving || !form.host || !form.display_name} style={{
            flex:1, padding:"10px", borderRadius:8, border:"none",
            background:"linear-gradient(135deg, #1a6cf5, #2d7fff)", color:"#fff", cursor:"pointer",
            fontFamily:"'DM Mono', monospace", fontSize:12, fontWeight:600,
            opacity: (!form.host || !form.display_name) ? 0.5 : 1
          }}>{saving ? "Saving…" : "Save Server"}</button>
        </div>
      </div>
    </div>
  );
}

// ── SERVER PANEL ──────────────────────────────────────────────────────────────
function ServerPanel({ server, isSelected, onClick }) {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const h = await api.health(server.id);
        if (!cancelled) { setHealth(h); setError(null); }
      } catch(e) { if (!cancelled) setError(e.message); }
    };
    load();
    const t = setInterval(load, POLL_MS);
    return () => { cancelled = true; clearInterval(t); };
  }, [server.id]);

  const statusColor = error ? "#ff4757" : health?.blocked_sessions > 0 ? "#ffd32a" : "#00e5a0";

  return (
    <div onClick={onClick} style={{
      padding:"12px 14px", borderRadius:10, cursor:"pointer",
      background: isSelected ? "rgba(26,108,245,0.12)" : "rgba(255,255,255,0.03)",
      border: `1px solid ${isSelected ? "rgba(26,108,245,0.4)" : "rgba(255,255,255,0.07)"}`,
      transition:"all 0.15s"
    }}>
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:6 }}>
        <div style={{ display:"flex", alignItems:"center", gap:8 }}>
          <Pulse color={statusColor} size={6}/>
          <span style={{ fontFamily:"'Syne', sans-serif", fontWeight:700, fontSize:13 }}>{server.display_name}</span>
        </div>
        <Badge text={server.role.replace("_"," ").toUpperCase()} color="#7a8aac"/>
      </div>
      <div style={{ fontFamily:"'DM Mono', monospace", fontSize:10, color:"#7a8aac", marginBottom:8 }}>{server.host}{server.port !== 1433 ? `:${server.port}` : ""}</div>
      {health && !error && (
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:6 }}>
          {[
            { label:"CPU", value:`${fmt(health.cpu_percent,0)}%`, color: health.cpu_percent > 90 ? "#ff4757" : health.cpu_percent > 70 ? "#ffd32a" : "#00e5a0" },
            { label:"MEM", value:fmtMem(health.memory_used_mb), color:"#00d4ff" },
            { label:"BLK", value:health.blocked_sessions ?? "—", color: health.blocked_sessions > 0 ? "#ff4757" : "#00e5a0" },
          ].map(s => (
            <div key={s.label} style={{ textAlign:"center", background:"rgba(0,0,0,0.2)", borderRadius:5, padding:"4px 0" }}>
              <div style={{ fontSize:8, fontFamily:"'DM Mono', monospace", color:"#7a8aac", textTransform:"uppercase" }}>{s.label}</div>
              <div style={{ fontFamily:"'Syne', sans-serif", fontWeight:700, fontSize:13, color:s.color }}>{s.value}</div>
            </div>
          ))}
        </div>
      )}
      {error && <div style={{ fontSize:10, fontFamily:"'DM Mono', monospace", color:"#ff4757" }}>Connection failed</div>}
      {!health && !error && <div style={{ fontSize:10, fontFamily:"'DM Mono', monospace", color:"#7a8aac" }}>Loading…</div>}
    </div>
  );
}

// ── MAIN DETAIL VIEW ──────────────────────────────────────────────────────────
function ServerDetail({ server }) {
  const [health, setHealth] = useState(null);
  const [history, setHistory] = useState([]);
  const [sessions, setSessions] = useState(null);
  const [waits, setWaits] = useState([]);
  const [ag, setAG] = useState(null);
  const [fci, setFCI] = useState(null);
  const [logship, setLogship] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");
  const [loading, setLoading] = useState(true);

  const loadAll = useCallback(async () => {
    try {
      const [h, hist, s, w, agd, fcid, lsd] = await Promise.allSettled([
        api.health(server.id), api.history(server.id), api.sessions(server.id),
        api.waits(server.id), api.ag(server.id), api.fci(server.id), api.logship(server.id)
      ]);
      if (h.status === "fulfilled") setHealth(h.value);
      if (hist.status === "fulfilled") setHistory(hist.value.map(r => ({ t: new Date(r.captured_at).toLocaleTimeString(), v: r.cpu_percent || 0, m: (r.memory_used_mb||0)/1024, b: r.blocked_sessions || 0 })));
      if (s.status === "fulfilled") setSessions(s.value);
      if (w.status === "fulfilled") setWaits(w.value);
      if (agd.status === "fulfilled") setAG(agd.value);
      if (fcid.status === "fulfilled") setFCI(fcid.value);
      if (lsd.status === "fulfilled") setLogship(lsd.value);
    } finally { setLoading(false); }
  }, [server.id]);

  useEffect(() => {
    setLoading(true);
    setActiveTab("overview");
    loadAll();
    const t = setInterval(loadAll, POLL_MS);
    return () => clearInterval(t);
  }, [server.id, loadAll]);

  const tabs = ["overview", "sessions", "waits", "clusters", "logship"];
  const tabLabel = { overview:"Overview", sessions:"Sessions", waits:"Wait Stats", clusters:"AG / FCI", logship:"Log Shipping" };

  const panel = {
    background:"rgba(255,255,255,0.03)", border:"1px solid rgba(255,255,255,0.07)",
    borderRadius:10, padding:16
  };

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:16, animation:"fadeIn 0.3s ease" }}>
      {/* Header */}
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between" }}>
        <div>
          <h2 style={{ fontFamily:"'Syne', sans-serif", fontWeight:800, fontSize:22, margin:0 }}>{server.display_name}</h2>
          <div style={{ fontFamily:"'DM Mono', monospace", fontSize:11, color:"#7a8aac", marginTop:2 }}>
            {server.host} · {server.auth_type.replace("_"," ").toUpperCase()} · {health?.server_props?.version?.split("\n")[0]?.split(" ").slice(0,4).join(" ") || ""}
          </div>
        </div>
        <div style={{ display:"flex", gap:6 }}>
          <Badge text={server.role.replace(/_/g," ").toUpperCase()} color="#1a6cf5"/>
          {loading && <Badge text="LOADING" color="#7a8aac"/>}
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display:"flex", gap:4, borderBottom:"1px solid rgba(255,255,255,0.07)", paddingBottom:0 }}>
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)} style={{
            background: activeTab===t ? "rgba(26,108,245,0.15)" : "none",
            border: "none", borderBottom: activeTab===t ? "2px solid #1a6cf5" : "2px solid transparent",
            color: activeTab===t ? "#f0f4ff" : "#7a8aac", cursor:"pointer", padding:"8px 14px",
            fontFamily:"'DM Mono', monospace", fontSize:11, letterSpacing:"0.05em",
            transition:"all 0.15s"
          }}>{tabLabel[t]}</button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === "overview" && (
        <>
          <div style={{ display:"flex", gap:10 }}>
            <StatCard label="CPU" value={fmt(health?.cpu_percent,0)} unit="%" color={health?.cpu_percent > 90 ? "#ff4757" : health?.cpu_percent > 70 ? "#ffd32a" : "#00e5a0"} chart={history.map(r=>({v:r.v}))}/>
            <StatCard label="Memory Used" value={fmtMem(health?.memory_used_mb)} color="#00d4ff" sub={health?.memory_total_mb ? `of ${fmtMem(health.memory_total_mb)}` : ""} chart={history.map(r=>({v:r.m}))}/>
            <StatCard label="Active Sessions" value={health?.active_sessions ?? "—"} color="#a158ff" chart={[]}/>
            <StatCard label="Blocked" value={health?.blocked_sessions ?? "—"} color={health?.blocked_sessions > 0 ? "#ff4757" : "#00e5a0"} chart={history.map(r=>({v:r.b}))}/>
          </div>

          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
            <div style={panel}>
              <SectionHeader label="CPU History (4h)" icon="📈"/>
              <div style={{ height:120 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={history} margin={{top:4,right:0,bottom:0,left:-20}}>
                    <XAxis dataKey="t" tick={{fontSize:9, fill:"#7a8aac", fontFamily:"'DM Mono', monospace"}} interval="preserveStartEnd" tickLine={false} axisLine={false}/>
                    <YAxis tick={{fontSize:9, fill:"#7a8aac"}} tickLine={false} axisLine={false} domain={[0,100]}/>
                    <Tooltip contentStyle={{background:"#0d1428", border:"1px solid rgba(255,255,255,0.1)", borderRadius:8, fontSize:11, fontFamily:"'DM Mono', monospace"}} labelStyle={{color:"#7a8aac"}} itemStyle={{color:"#00e5a0"}}/>
                    <Area type="monotone" dataKey="v" name="CPU %" stroke="#00e5a0" fill="rgba(0,229,160,0.1)" strokeWidth={1.5} dot={false} isAnimationActive={false}/>
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div style={panel}>
              <SectionHeader label="Memory History (4h)" icon="🧠"/>
              <div style={{ height:120 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={history} margin={{top:4,right:0,bottom:0,left:-20}}>
                    <XAxis dataKey="t" tick={{fontSize:9, fill:"#7a8aac", fontFamily:"'DM Mono', monospace"}} interval="preserveStartEnd" tickLine={false} axisLine={false}/>
                    <YAxis tick={{fontSize:9, fill:"#7a8aac"}} tickLine={false} axisLine={false}/>
                    <Tooltip contentStyle={{background:"#0d1428", border:"1px solid rgba(255,255,255,0.1)", borderRadius:8, fontSize:11, fontFamily:"'DM Mono', monospace"}} labelStyle={{color:"#7a8aac"}} itemStyle={{color:"#00d4ff"}}/>
                    <Area type="monotone" dataKey="m" name="Memory GB" stroke="#00d4ff" fill="rgba(0,212,255,0.1)" strokeWidth={1.5} dot={false} isAnimationActive={false}/>
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <div style={panel}>
            <SectionHeader label="Databases" icon="🗃️"/>
            <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
              {health?.databases?.map((db, i) => (
                <div key={i} style={{
                  padding:"6px 10px", background:"rgba(255,255,255,0.03)", border:"1px solid rgba(255,255,255,0.07)",
                  borderRadius:6, display:"flex", alignItems:"center", gap:8
                }}>
                  <Pulse color={db.state_desc === "ONLINE" ? "#00e5a0" : "#ff4757"} size={5}/>
                  <span style={{ fontFamily:"'DM Mono', monospace", fontSize:11, color:"#c0cce0" }}>{db.name}</span>
                  <Badge text={db.state_desc} color={db.state_desc === "ONLINE" ? "#00e5a0" : "#ff4757"}/>
                  <span style={{ fontSize:10, color:"#7a8aac", fontFamily:"'DM Mono', monospace" }}>{fmt(db.size_mb,0)} MB</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {/* Sessions Tab */}
      {activeTab === "sessions" && (
        <div style={panel}>
          <SectionHeader label={`Blocked Sessions (${sessions?.blocked_sessions ?? 0})`} icon="🔒"/>
          <BlockedPanel sessions={sessions}/>
        </div>
      )}

      {/* Waits Tab */}
      {activeTab === "waits" && (
        <div style={panel}>
          <SectionHeader label="Top Wait Stats" icon="⏱️"/>
          <WaitBars waits={waits}/>
        </div>
      )}

      {/* Clusters Tab */}
      {activeTab === "clusters" && (
        <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
          <div style={panel}>
            <SectionHeader label="Availability Groups" icon="🔄"/>
            <AGPanel data={ag}/>
          </div>
          <div style={panel}>
            <SectionHeader label="Failover Cluster (FCI)" icon="🖥️"/>
            <FCIPanel data={fci}/>
          </div>
        </div>
      )}

      {/* Log Shipping Tab */}
      {activeTab === "logship" && (
        <div style={panel}>
          <SectionHeader label="Log Shipping Status" icon="📦"/>
          <LogShipPanel data={logship}/>
        </div>
      )}
    </div>
  );
}

// ── ALERTS SIDEBAR ────────────────────────────────────────────────────────────
function AlertsPanel({ onClose }) {
  const [events, setEvents] = useState([]);
  useEffect(() => { api.alerts().then(setEvents).catch(()=>{}); }, []);
  const sev = { critical:"#ff4757", warning:"#ffd32a", info:"#00d4ff" };
  return (
    <div style={{ position:"fixed", inset:0, background:"rgba(0,0,0,0.6)", backdropFilter:"blur(6px)", zIndex:500, display:"flex", justifyContent:"flex-end" }}>
      <div style={{ width: Math.min(420, window.innerWidth), background:"#0d1428", borderLeft:"1px solid rgba(255,255,255,0.08)", height:"100%", overflowY:"auto", padding:24 }}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:20 }}>
          <span style={{ fontFamily:"'Syne', sans-serif", fontWeight:800, fontSize:18 }}>Alert Events</span>
          <button onClick={onClose} style={{ background:"none", border:"none", color:"#7a8aac", cursor:"pointer", fontSize:20 }}>✕</button>
        </div>
        {events.length === 0 && <div style={{ color:"#7a8aac", textAlign:"center", padding:"40px 0", fontFamily:"'DM Mono', monospace", fontSize:12 }}>No alerts in last 24h</div>}
        <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
          {events.map((e, i) => (
            <div key={i} style={{
              padding:"10px 12px", borderRadius:8,
              background: `${sev[e.severity] || "#7a8aac"}0d`,
              border:`1px solid ${sev[e.severity] || "#7a8aac"}30`,
              borderLeft:`3px solid ${sev[e.severity] || "#7a8aac"}`
            }}>
              <div style={{ display:"flex", justifyContent:"space-between", marginBottom:4 }}>
                <Badge text={e.severity?.toUpperCase()} color={sev[e.severity]}/>
                <span style={{ fontSize:10, color:"#7a8aac", fontFamily:"'DM Mono', monospace" }}>{ago(e.fired_at)}</span>
              </div>
              <div style={{ fontFamily:"'DM Mono', monospace", fontSize:11, color:"#c0cce0" }}>{e.message}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── ROOT APP ──────────────────────────────────────────────────────────────────
export default function App() {
  const [servers, setServers] = useState([]);
  const [selected, setSelected] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [showAlerts, setShowAlerts] = useState(false);
  const [unacked, setUnacked] = useState(0);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const loadServers = useCallback(async () => {
    try {
      const s = await api.servers();
      setServers(s);
      if (s.length > 0 && !selected) setSelected(s[0]);
    } catch(e) { console.error("Failed to load servers:", e); }
  }, [selected]);

  useEffect(() => {
    loadServers();
    const t = setInterval(loadServers, 60000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const load = () => api.unacked().then(r => setUnacked(r.count || 0)).catch(()=>{});
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, []);

  return (
    <div style={{ display:"flex", flexDirection:"column", height:"100vh", background:"#0a0f1e", color:"#f0f4ff", fontFamily:"'Inter', sans-serif", overflow:"hidden" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@400;500&family=Inter:wght@400;500&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }
        @keyframes pulseRing { 0%,100% { transform: scale(1); opacity: 0.25; } 50% { transform: scale(1.8); opacity: 0; } }
        @keyframes fadeIn { from { opacity:0; transform: translateY(8px); } to { opacity:1; transform: translateY(0); } }
        body { background: #0a0f1e; }
        input:focus, select:focus { border-color: rgba(26,108,245,0.5) !important; }
        input[type=checkbox] { accent-color: #1a6cf5; }
      `}</style>

      {/* ── TOP NAV ── */}
      <div style={{
        height:52, background:"rgba(13,20,40,0.95)", borderBottom:"1px solid rgba(255,255,255,0.07)",
        display:"flex", alignItems:"center", justifyContent:"space-between",
        paddingLeft: 20, backdropFilter:"blur(20px)", flexShrink:0, zIndex:10,
        WebkitAppRegion: "drag"
      }}>
        <div style={{ display:"flex", alignItems:"center", gap:14, WebkitAppRegion: "no-drag" }}>
          <button onClick={() => setSidebarOpen(o=>!o)} style={{ background:"none", border:"none", color:"#7a8aac", cursor:"pointer", fontSize:18, padding:2 }}>☰</button>
          <div style={{ display:"flex", alignItems:"center", gap:8 }}>
            <span style={{ fontSize:18 }}>🗄️</span>
            <span style={{ fontFamily:"'Syne', sans-serif", fontWeight:800, fontSize:16, letterSpacing:"-0.02em" }}>MSSQL Dashboard</span>
            <span style={{ fontFamily:"'DM Mono', monospace", fontSize:10, color:"#7a8aac", background:"rgba(255,255,255,0.05)", padding:"2px 6px", borderRadius:4 }}>v1.0.0</span>
          </div>
        </div>

        <div style={{ display:"flex", alignItems:"center" }}>
          <div style={{ display:"flex", alignItems:"center", gap:8, WebkitAppRegion: "no-drag" }}>
            <div style={{ fontFamily:"'DM Mono', monospace", fontSize:10, color:"#7a8aac", display:"flex", alignItems:"center", gap:5 }}>
              <Pulse color="#00e5a0" size={5}/>
              {servers.filter(s=>s.enabled).length} servers monitored
            </div>
            <button onClick={() => setShowAlerts(true)} style={{
              background: unacked > 0 ? "rgba(255,71,87,0.15)" : "rgba(255,255,255,0.05)",
              border: `1px solid ${unacked > 0 ? "rgba(255,71,87,0.3)" : "rgba(255,255,255,0.1)"}`,
              color: unacked > 0 ? "#ff4757" : "#7a8aac", borderRadius:8, padding:"6px 12px",
              cursor:"pointer", fontFamily:"'DM Mono', monospace", fontSize:11, display:"flex", alignItems:"center", gap:6
            }}>
              🔔 {unacked > 0 ? `${unacked} unacked` : "Alerts"}
            </button>
            <ImportServerButton onImportSuccess={loadServers} />
            <button onClick={() => setShowAdd(true)} style={{
              background:"linear-gradient(135deg, #1a6cf5, #2d7fff)", border:"none",
              color:"#fff", borderRadius:8, padding:"6px 14px", cursor:"pointer",
              fontFamily:"'DM Mono', monospace", fontSize:11, fontWeight:600
            }}>+ Add Server</button>
          </div>
          <WindowControls />
        </div>
      </div>

      {/* ── BODY ── */}
      <div style={{ display:"flex", flex:1, overflow:"hidden" }}>

        {/* Sidebar */}
        {sidebarOpen && (
          <div style={{
            width:260, background:"rgba(13,20,40,0.6)", borderRight:"1px solid rgba(255,255,255,0.07)",
            display:"flex", flexDirection:"column", overflow:"hidden", flexShrink:0
          }}>
            <div style={{ padding:"12px 14px 8px", fontFamily:"'DM Mono', monospace", fontSize:10, color:"#7a8aac", textTransform:"uppercase", letterSpacing:"0.1em" }}>
              Servers ({servers.length})
            </div>
            <div style={{ flex:1, overflowY:"auto", padding:"0 10px 10px" }}>
              {servers.length === 0 ? (
                <div style={{ textAlign:"center", padding:"40px 16px" }}>
                  <div style={{ fontSize:32, marginBottom:12 }}>🗄️</div>
                  <div style={{ fontFamily:"'DM Mono', monospace", fontSize:11, color:"#7a8aac", marginBottom:16 }}>No servers yet</div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    <ImportServerButton onImportSuccess={loadServers} style={{ width: "100%", padding: "8px 16px" }} />
                    <button onClick={() => setShowAdd(true)} style={{
                      background:"linear-gradient(135deg, #1a6cf5, #2d7fff)", border:"none",
                      color:"#fff", borderRadius:8, padding:"8px 16px", cursor:"pointer",
                      fontFamily:"'DM Mono', monospace", fontSize:11, fontWeight:600, width: "100%"
                    }}>+ Add Manually</button>
                  </div>
                </div>
              ) : (
                <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                  {servers.map(s => (
                    <ServerPanel key={s.id} server={s} isSelected={selected?.id === s.id} onClick={() => setSelected(s)}/>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Main content */}
        <div style={{ flex:1, overflowY:"auto", padding:20 }}>
          {selected ? (
            <ServerDetail server={selected}/>
          ) : (
            <div style={{ display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", height:"100%", gap:16 }}>
              <div style={{ fontSize:64 }}>🗄️</div>
              <h2 style={{ fontFamily:"'Syne', sans-serif", fontWeight:800, fontSize:24 }}>MSSQL Dashboard</h2>
              <p style={{ color:"#7a8aac", fontFamily:"'DM Mono', monospace", fontSize:12 }}>Add servers to start monitoring</p>
              <div style={{ display: "flex", gap: 12 }}>
                <ImportServerButton onImportSuccess={loadServers} style={{ padding: "12px 28px", fontSize: 13 }} />
                <button onClick={() => setShowAdd(true)} style={{
                  background:"linear-gradient(135deg, #1a6cf5, #2d7fff)", border:"none",
                  color:"#fff", borderRadius:10, padding:"12px 28px", cursor:"pointer",
                  fontFamily:"'DM Mono', monospace", fontSize:13, fontWeight:600
                }}>+ Add Manually</button>
              </div>
            </div>
          )}
        </div>
      </div>

      {showAdd && <AddServerModal onClose={() => setShowAdd(false)} onSaved={loadServers}/>}
      {showAlerts && <AlertsPanel onClose={() => setShowAlerts(false)}/>}
    </div>
  );
}