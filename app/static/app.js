let chart;
const $ = (id) => document.getElementById(id);
function toast(message) {
  const el = $("toast"); el.textContent = message; el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2600);
}
async function api(path, options={}) {
  const response = await fetch(path, {headers: {"Content-Type":"application/json"}, ...options});
  if (!response.ok) {
    let detail = response.statusText;
    try { detail = (await response.json()).detail || detail; } catch {}
    throw new Error(detail);
  }
  return response.json();
}
function formatTime(value) {
  if (!value) return "No data";
  return new Date(value).toLocaleString([], {month:"short", day:"numeric", hour:"2-digit", minute:"2-digit"});
}
async function loadSummary() {
  const s = await api("/api/summary");
  $("total-devices").textContent = s.total_devices;
  $("online-devices").textContent = s.online_devices;
  $("total-readings").textContent = s.total_readings.toLocaleString();
  $("active-alerts").textContent = s.active_alerts;
  $("avg-temperature").textContent = Number(s.average_temperature).toFixed(1);
  $("side-alert-count").textContent = s.active_alerts;
  $("alert-chip").textContent = `${s.active_alerts} active`;
}
async function loadDevices() {
  const devices = await api("/api/devices");
  $("device-rows").innerHTML = devices.length ? devices.map(d => `
    <tr><td><div class="device-name">${escapeHtml(d.name)}</div><div class="device-id">${escapeHtml(d.device_id)}</div></td>
    <td>${escapeHtml(d.location)}</td><td><span class="status">${escapeHtml(d.status)}</span></td>
    <td class="temp">${d.last_temperature == null ? "—" : Number(d.last_temperature).toFixed(1)+" °C"}</td>
    <td>${formatTime(d.last_seen)}</td></tr>`).join("") : '<tr><td colspan="5" class="empty">No devices registered. Generate demo data to get started.</td></tr>';
}
function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
async function loadAlerts() {
  const alerts = await api("/api/alerts");
  const active = alerts.filter(a => !a.acknowledged);
  $("alert-list").innerHTML = alerts.length ? alerts.slice(0,8).map(a => `
    <div class="alert-item"><div class="alert-mark">⚑</div><div class="alert-copy">
    <strong>${escapeHtml(a.message)}</strong><small>${escapeHtml(a.device_id)} · ${formatTime(a.created_at)}</small></div>
    <span class="severity">${escapeHtml(a.severity)}</span>
    ${a.acknowledged ? '<span class="healthy">ACK</span>' : `<button class="ack-btn" data-ack="${a.id}">Acknowledge</button>`}</div>`).join("") : '<div class="empty">No alerts. Your devices are looking good.</div>';
  document.querySelectorAll("[data-ack]").forEach(btn => btn.addEventListener("click", async () => {
    try { await api(`/api/alerts/${btn.dataset.ack}/acknowledge`, {method:"POST"}); toast("Alert acknowledged"); await refreshAll(); }
    catch(e) { toast(e.message); }
  }));
}
async function loadChart() {
  const hours = $("range-select").value;
  const rows = await api(`/api/series?hours=${hours}`);
  const labels = rows.map(r => new Date(r.time).toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"}));
  const temps = rows.map(r => r.temperature);
  const humidity = rows.map(r => r.humidity);
  if (chart) chart.destroy();
  chart = new Chart($("telemetry-chart"), {
    type:"line",
    data:{labels,datasets:[
      {label:"Temperature °C",data:temps,borderColor:"#806ff0",backgroundColor:"#806ff018",fill:true,tension:.38,pointRadius:2,borderWidth:2},
      {label:"Humidity %",data:humidity,borderColor:"#58a3ec",backgroundColor:"transparent",tension:.38,pointRadius:0,borderWidth:1.7}
    ]},
    options:{responsive:true,maintainAspectRatio:false,interaction:{mode:"index",intersect:false},
      plugins:{legend:{display:false}},scales:{
        x:{grid:{display:false},ticks:{color:"#a0a1b0",maxTicksLimit:8,font:{size:9}}},
        y:{grid:{color:"#f0f0f5"},ticks:{color:"#a0a1b0",font:{size:9}}}
      }}
  });
}
async function refreshAll() {
  try { await Promise.all([loadSummary(),loadDevices(),loadAlerts(),loadChart()]); }
  catch(e) { toast(`Could not load dashboard: ${e.message}`); }
}
$("generate-btn").addEventListener("click", async () => {
  const btn = $("generate-btn"); btn.disabled = true; btn.textContent = "Generating…";
  try { const result = await api("/api/demo/generate",{method:"POST"}); toast(`${result.readings_generated} demo readings generated`); await refreshAll(); }
  catch(e) { toast(e.message); }
  finally { btn.disabled = false; btn.textContent = "＋ Generate demo data"; }
});
$("refresh-btn").addEventListener("click", refreshAll);
$("range-select").addEventListener("change", loadChart);
refreshAll();
setInterval(refreshAll, 30000);
