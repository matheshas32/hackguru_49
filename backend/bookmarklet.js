javascript:(function(){
  const url = window.location.href;
  const overlay = document.createElement("div");
  overlay.style.cssText = "position:fixed;top:20px;right:20px;z-index:9999999;background:#111827;color:#fff;padding:16px;border-radius:14px;border:1.5px solid #6366f1;box-shadow:0 10px 30px rgba(0,0,0,0.8);font-family:sans-serif;max-width:320px;";
  overlay.innerHTML = "<div style=\"font-size:13px;font-weight:700;\">🛡️ EventTrust AI</div><div style=\"font-size:11px;color:#94a3b8;margin-top:4px;\">Scanning poster on current page...</div>";
  document.body.appendChild(overlay);

  fetch("http://127.0.0.1:8000/api/verify-url", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({url: url})
  })
  .then(r => r.json())
  .then(data => {
    const isReal = data.verification.poster_result === "REAL";
    const v = data.verification;
    overlay.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <strong style="color:${isReal ? "#34d399" : "#f87171"};font-size:14px;">${isReal ? "🟢 AUTHENTIC POSTER" : "🔴 SUSPICIOUS"}</strong>
        <span style="font-size:14px;font-weight:800;font-family:monospace;">${v.trust_score}/100</span>
      </div>
      <div style="font-size:11px;color:#cbd5e1;line-height:1.4;">
        <div><strong>Model:</strong> ${v.real_probability}% Real (${v.poster_confidence}% Conf)</div>
        <div><strong>QR Code:</strong> ${v.qr_status} (${v.qr_result})</div>
        ${v.qr_data ? `<div style="word-break:break-all;color:#38bdf8;margin-top:4px;">QR: ${v.qr_data}</div>` : ""}
      </div>
      <button onclick="this.parentElement.remove()" style="margin-top:10px;width:100%;padding:4px 8px;background:rgba(255,255,255,0.1);border:none;color:#fff;border-radius:6px;cursor:pointer;font-size:11px;">Close</button>
    `;
  })
  .catch(err => {
    overlay.innerHTML = `<div style="color:#f87171;font-size:12px;"><strong>Scan Failed:</strong><br>${err.message}<br><br><small>Make sure EventTrust backend is running on http://127.0.0.1:8000</small></div><button onclick="this.parentElement.remove()" style="margin-top:8px;padding:3px 6px;background:#333;color:#fff;border:none;border-radius:4px;">Close</button>`;
  });
})();
