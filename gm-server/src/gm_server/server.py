import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from gm_server.models.game_state import GameState
from gm_server.models.commands import Command, TickResponse
from gm_server.logic.decision_loop import DecisionLoop
from gm_server.logic.state_manager import StateManager

logger = logging.getLogger(__name__)


# --- Request/response models for non-tick endpoints ---


class DirectiveRequest(BaseModel):
    text: str
    priority: str = "normal"  # low/normal/high/critical
    ttl_ticks: int = 10


class OverrideRequest(BaseModel):
    commands: list[Command]


class ControlRequest(BaseModel):
    action: str  # "pause" or "resume"


# --- App factory ---


def create_app(decision_loop: DecisionLoop, state_manager: StateManager) -> FastAPI:
    app = FastAPI(title="Arma 3 Game Master", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Store references on app state
    app.state.decision_loop = decision_loop
    app.state.state_manager = state_manager

    @app.post("/api/v1/tick", response_model=TickResponse)
    async def tick(game_state: GameState):
        """Main game tick: receive state, return commands."""
        try:
            response = await app.state.decision_loop.process_tick(game_state)
            return response
        except Exception as e:
            logger.exception("Tick processing failed")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/v1/directive")
    async def add_directive(req: DirectiveRequest):
        """Add operator directive to LLM prompt."""
        app.state.state_manager.add_directive(req.text, req.priority, req.ttl_ticks)
        return {"status": "ok", "message": f"Directive added (ttl={req.ttl_ticks} ticks)"}

    @app.post("/api/v1/override")
    async def add_override(req: OverrideRequest):
        """Queue direct commands bypassing LLM."""
        app.state.state_manager.add_override(req.commands)
        return {"status": "ok", "message": f"{len(req.commands)} commands queued"}

    @app.post("/api/v1/control")
    async def control(req: ControlRequest):
        """Pause/resume LLM decision-making."""
        if req.action == "pause":
            app.state.state_manager.state.paused = True
            return {"status": "ok", "message": "GM paused -- only override commands will execute"}
        elif req.action == "resume":
            app.state.state_manager.state.paused = False
            return {"status": "ok", "message": "GM resumed"}
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {req.action}")

    @app.get("/api/v1/status")
    async def status():
        """Get current state summary."""
        summary = app.state.state_manager.get_state_summary()
        summary["tick_log"] = app.state.decision_loop.tick_log[-10:]
        pacing = app.state.decision_loop.pacing.info
        summary["pacing_phase"] = pacing.current_phase.value
        summary["intensity"] = pacing.intensity
        return summary

    @app.get("/ui", response_class=HTMLResponse)
    async def operator_ui():
        """Serve operator web UI."""
        return OPERATOR_UI_HTML

    return app


# ---------------------------------------------------------------------------
# Operator console -- single-page HTML with inline CSS / JS
# ---------------------------------------------------------------------------

OPERATOR_UI_HTML = (
    '<!DOCTYPE html>\n'
    '<html lang="en">\n'
    "<head>\n"
    '<meta charset="UTF-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
    "<title>ARMA 3 GM - Operator Console</title>\n"
    "<style>\n"
    "*{margin:0;padding:0;box-sizing:border-box}\n"
    "body{\n"
    "  background:#1a1a2e;color:#a0d2a0;\n"
    "  font-family:'Courier New',Courier,monospace;font-size:13px;\n"
    "  padding:8px;\n"
    "}\n"
    "h1{\n"
    "  text-align:center;letter-spacing:4px;font-size:16px;\n"
    "  color:#00ff41;border-bottom:1px solid #333;padding-bottom:6px;margin-bottom:8px;\n"
    "}\n"
    ".status-bar{\n"
    "  display:flex;gap:18px;flex-wrap:wrap;\n"
    "  background:#0d0d1a;border:1px solid #333;padding:6px 12px;margin-bottom:8px;\n"
    "  font-size:12px;\n"
    "}\n"
    ".status-bar span{margin-right:6px}\n"
    ".status-bar .label{color:#888}\n"
    ".status-bar .val{color:#00ff41;font-weight:bold}\n"
    ".paused-indicator{color:#ff4444;font-weight:bold;display:none}\n"
    "\n"
    ".grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px}\n"
    "@media(max-width:900px){.grid{grid-template-columns:1fr}}\n"
    "\n"
    ".panel{\n"
    "  background:#0d0d1a;border:1px solid #333;padding:8px;\n"
    "  max-height:320px;overflow-y:auto;\n"
    "}\n"
    ".panel-title{\n"
    "  color:#e0c040;font-size:12px;font-weight:bold;letter-spacing:2px;\n"
    "  border-bottom:1px solid #333;padding-bottom:4px;margin-bottom:6px;\n"
    "}\n"
    "\n"
    "table{width:100%;border-collapse:collapse;font-size:11px}\n"
    "th{color:#888;text-align:left;padding:2px 6px;border-bottom:1px solid #333;white-space:nowrap}\n"
    "td{padding:2px 6px;border-bottom:1px solid #1a1a2e;white-space:nowrap}\n"
    "tr:hover td{background:#16213e}\n"
    "\n"
    ".obj-row{display:flex;justify-content:space-between;padding:2px 0;"
    "border-bottom:1px solid #1a1a2e}\n"
    ".obj-name{color:#a0d2a0}.obj-status{font-weight:bold}\n"
    "\n"
    ".form-section{\n"
    "  background:#0d0d1a;border:1px solid #333;padding:8px;margin-bottom:8px;\n"
    "}\n"
    ".form-section .panel-title{margin-bottom:6px}\n"
    ".form-row{display:flex;gap:6px;align-items:flex-end;flex-wrap:wrap;margin-bottom:6px}\n"
    ".form-row label{color:#888;font-size:11px;display:flex;flex-direction:column;gap:2px}\n"
    "textarea,input[type=number],select{\n"
    "  background:#0a0a1a;color:#a0d2a0;border:1px solid #444;\n"
    "  font-family:'Courier New',monospace;font-size:12px;padding:4px;\n"
    "}\n"
    "textarea{width:100%;resize:vertical}\n"
    "select,input[type=number]{height:28px}\n"
    "button{\n"
    "  background:#16213e;color:#00ff41;border:1px solid #00ff41;\n"
    "  font-family:'Courier New',monospace;font-size:12px;\n"
    "  padding:4px 14px;cursor:pointer;\n"
    "}\n"
    "button:hover{background:#1a3a5c}\n"
    "button.danger{color:#ff4444;border-color:#ff4444}\n"
    "button.danger:hover{background:#3a1616}\n"
    "\n"
    ".controls{display:flex;gap:8px;margin-bottom:8px}\n"
    "\n"
    ".tick-log{\n"
    "  background:#0d0d1a;border:1px solid #333;padding:8px;\n"
    "  max-height:300px;overflow-y:auto;\n"
    "}\n"
    ".tick-entry{border-bottom:1px solid #222;padding:4px 0;margin-bottom:4px}\n"
    ".tick-entry .tick-header{color:#e0c040;font-size:11px;margin-bottom:2px}\n"
    ".tick-entry .tick-reasoning{color:#888;font-size:11px;font-style:italic;margin-bottom:2px}\n"
    ".tick-entry .tick-cmd{color:#a0d2a0;font-size:11px;margin-left:10px}\n"
    ".tick-src{font-size:10px;color:#555}\n"
    "\n"
    ".feedback{font-size:11px;margin-top:4px;min-height:14px}\n"
    ".feedback.ok{color:#00ff41}\n"
    ".feedback.err{color:#ff4444}\n"
    "\n"
    ".status-green{color:#00ff41}\n"
    ".status-amber{color:#e0c040}\n"
    ".status-red{color:#ff4444}\n"
    ".status-gray{color:#888}\n"
    "</style>\n"
    "</head>\n"
    "<body>\n"
    "<h1>ARMA 3 GAME MASTER &#8212; OPERATOR CONSOLE</h1>\n"
    "\n"
    "<!-- Status bar -->\n"
    '<div class="status-bar" id="statusBar">\n'
    '  <div><span class="label">TICK:</span><span class="val" id="sTick">&#8212;</span></div>\n'
    '  <div><span class="label">MISSION TIME:</span>'
    '<span class="val" id="sTime">&#8212;</span></div>\n'
    '  <div><span class="label">PHASE:</span>'
    '<span class="val" id="sPhase">&#8212;</span></div>\n'
    '  <div><span class="label">INTENSITY:</span>'
    '<span class="val" id="sIntensity">&#8212;</span></div>\n'
    '  <div class="paused-indicator" id="sPaused">[ PAUSED ]</div>\n'
    "</div>\n"
    "\n"
    "<!-- Forces + Objectives -->\n"
    '<div class="grid">\n'
    '  <div class="panel">\n'
    '    <div class="panel-title">FORCES</div>\n'
    "    <table>\n"
    "      <thead><tr>\n"
    "        <th>ID</th><th>Type</th><th>Status</th><th>Position</th>\n"
    "        <th>Size</th><th>HP</th><th>Ammo</th><th>Order</th>\n"
    "      </tr></thead>\n"
    '      <tbody id="forcesBody"></tbody>\n'
    "    </table>\n"
    "  </div>\n"
    '  <div class="panel">\n'
    '    <div class="panel-title">OBJECTIVES</div>\n'
    '    <div id="objectivesBody"></div>\n'
    "  </div>\n"
    "</div>\n"
    "\n"
    "<!-- Directive form -->\n"
    '<div class="form-section">\n'
    '  <div class="panel-title">OPERATOR DIRECTIVE</div>\n'
    '  <div class="form-row">\n'
    '    <label style="flex:1">Text\n'
    '      <textarea id="dirText" rows="2"'
    ' placeholder="e.g. Focus defense on the church"></textarea>\n'
    "    </label>\n"
    "    <label>Priority\n"
    '      <select id="dirPriority">\n'
    '        <option value="low">low</option>\n'
    '        <option value="normal" selected>normal</option>\n'
    '        <option value="high">high</option>\n'
    '        <option value="critical">critical</option>\n'
    "      </select>\n"
    "    </label>\n"
    "    <label>TTL\n"
    '      <input id="dirTTL" type="number" value="10" min="1" max="100"'
    ' style="width:60px">\n'
    "    </label>\n"
    '    <button onclick="sendDirective()">SEND</button>\n'
    "  </div>\n"
    '  <div class="feedback" id="dirFeedback"></div>\n'
    "</div>\n"
    "\n"
    "<!-- Override form -->\n"
    '<div class="form-section">\n'
    '  <div class="panel-title">COMMAND OVERRIDE</div>\n'
    '  <div class="form-row">\n'
    '    <label style="flex:1">Commands (JSON array)\n'
    '      <textarea id="overrideJSON" rows="3"'
    ' placeholder=\'[{"action":"move_squad","params":{"unit":"grp_alpha_1",'
    '"to":"agia_marina_church","task":"defend"}}]\'>'
    "</textarea>\n"
    "    </label>\n"
    '    <button onclick="sendOverride()">SEND</button>\n'
    "  </div>\n"
    '  <div class="feedback" id="ovrFeedback"></div>\n'
    "</div>\n"
    "\n"
    "<!-- Control buttons -->\n"
    '<div class="controls">\n'
    '  <button onclick="sendControl(\'pause\')" class="danger">PAUSE GM</button>\n'
    '  <button onclick="sendControl(\'resume\')">RESUME GM</button>\n'
    '  <div class="feedback" id="ctrlFeedback"></div>\n'
    "</div>\n"
    "\n"
    "<!-- Tick log -->\n"
    '<div class="tick-log">\n'
    '  <div class="panel-title">TICK LOG (last 10)</div>\n'
    '  <div id="tickLog"><span class="status-gray">Waiting for data...</span></div>\n'
    "</div>\n"
    "\n"
    "<script>\n"
    "var API = window.location.origin + '/api/v1';\n"
    "\n"
    "function statusColor(val) {\n"
    "  if (val >= 0.7) return 'status-red';\n"
    "  if (val >= 0.4) return 'status-amber';\n"
    "  return 'status-green';\n"
    "}\n"
    "\n"
    "function phaseColor(phase) {\n"
    "  var m = {calm:'status-green', buildup:'status-amber',"
    " peak:'status-red', relax:'status-green'};\n"
    "  return m[phase] || 'status-gray';\n"
    "}\n"
    "\n"
    "function unitStatusColor(s) {\n"
    "  if (s === 'engaging' || s === 'retreating') return 'status-red';\n"
    "  if (s === 'moving' || s === 'fortifying') return 'status-amber';\n"
    "  return 'status-green';\n"
    "}\n"
    "\n"
    "function threatColor(t) {\n"
    "  if (t === 'high' || t === 'contested') return 'status-red';\n"
    "  if (t === 'medium') return 'status-amber';\n"
    "  return 'status-green';\n"
    "}\n"
    "\n"
    "function formatTime(sec) {\n"
    "  if (sec == null) return '\\u2014';\n"
    "  var m = Math.floor(sec / 60), s = Math.floor(sec % 60);\n"
    "  return String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');\n"
    "}\n"
    "\n"
    "function esc(s) {\n"
    "  if (s == null) return '';\n"
    "  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');\n"
    "}\n"
    "\n"
    "function showFeedback(id, msg, ok) {\n"
    "  var el = document.getElementById(id);\n"
    "  el.textContent = msg;\n"
    "  el.className = 'feedback ' + (ok ? 'ok' : 'err');\n"
    "  setTimeout(function() { el.textContent = ''; }, 5000);\n"
    "}\n"
    "\n"
    "function renderStatus(d) {\n"
    "  document.getElementById('sTick').textContent = d.tick != null ? d.tick : '\\u2014';\n"
    "  document.getElementById('sTime').textContent = formatTime(d.mission_time);\n"
    "\n"
    "  var phase = d.pacing_phase || '\\u2014';\n"
    "  var phaseEl = document.getElementById('sPhase');\n"
    "  phaseEl.textContent = phase;\n"
    "  phaseEl.className = 'val ' + phaseColor(phase);\n"
    "\n"
    "  var intensity = d.intensity != null ? d.intensity : 0;\n"
    "  var intEl = document.getElementById('sIntensity');\n"
    "  intEl.textContent = intensity.toFixed(2);\n"
    "  intEl.className = 'val ' + statusColor(intensity);\n"
    "\n"
    "  document.getElementById('sPaused').style.display = d.paused ? 'block' : 'none';\n"
    "\n"
    "  // Forces table\n"
    "  var fb = document.getElementById('forcesBody');\n"
    "  var units = d.units || d.forces || [];\n"
    "  if (units.length) {\n"
    "    fb.innerHTML = units.map(function(f) {\n"
    "      var sc = unitStatusColor(f.status);\n"
    "      var hp = f.health != null ? String(f.health) : '\\u2014';\n"
    "      var ammo = f.ammo != null ? String(f.ammo) : '\\u2014';\n"
    "      return '<tr>' +\n"
    "        '<td>' + esc(f.id) + '</td>' +\n"
    "        '<td>' + esc(f.type) + '</td>' +\n"
    "        '<td class=\"' + sc + '\">' + esc(f.status) + '</td>' +\n"
    "        '<td>' + esc(f.position) + '</td>' +\n"
    "        '<td>' + (f.size != null ? f.size : '\\u2014') + '</td>' +\n"
    "        '<td>' + hp + '</td>' +\n"
    "        '<td>' + ammo + '</td>' +\n"
    "        '<td>' + esc(f.current_order || '\\u2014') + '</td></tr>';\n"
    "    }).join('');\n"
    "  } else {\n"
    "    fb.innerHTML = '<tr><td colspan=\"8\" class=\"status-gray\">"
    "No forces data</td></tr>';\n"
    "  }\n"
    "\n"
    "  // Objectives\n"
    "  var ob = document.getElementById('objectivesBody');\n"
    "  if (d.objectives && d.objectives.length) {\n"
    "    ob.innerHTML = d.objectives.map(function(o) {\n"
    "      var tc = threatColor(o.threat);\n"
    "      return '<div class=\"obj-row\">' +\n"
    "        '<span class=\"obj-name\">' + esc(o.id || o.name) + '</span>' +\n"
    "        '<span class=\"obj-status ' + tc + '\">' + esc(o.status) +"
    " ' [' + esc(o.threat) + ']</span></div>';\n"
    "    }).join('');\n"
    "  } else {\n"
    "    ob.innerHTML = '<div class=\"status-gray\">No objectives data</div>';\n"
    "  }\n"
    "\n"
    "  // Tick log\n"
    "  var tl = document.getElementById('tickLog');\n"
    "  if (d.tick_log && d.tick_log.length) {\n"
    "    tl.innerHTML = d.tick_log.slice().reverse().map(function(t) {\n"
    "      var cmds = (t.commands || []).map(function(c) {\n"
    "        return '<div class=\"tick-cmd\">' + esc(c.type || c.action) + ' ' +"
    " esc(JSON.stringify(c.params || {})) + '</div>';\n"
    "      }).join('');\n"
    "      var tid = t.tick_id != null ? t.tick_id : t.tick;\n"
    "      return '<div class=\"tick-entry\">' +\n"
    "        '<div class=\"tick-header\">Tick ' + tid + ' | ' +"
    " (t.commands||[]).length + ' cmds' +\n"
    "        ' <span class=\"tick-src\">[' + esc(t.source || 'llm') + ']</span></div>' +\n"
    "        (t.raw_response ? '<div class=\"tick-reasoning\">' +"
    " esc(t.raw_response) + '</div>' : '') +\n"
    "        cmds + '</div>';\n"
    "    }).join('');\n"
    "  } else {\n"
    "    tl.innerHTML = '<span class=\"status-gray\">No ticks recorded yet.</span>';\n"
    "  }\n"
    "}\n"
    "\n"
    "function refresh() {\n"
    "  fetch(API + '/status').then(function(r) {\n"
    "    if (!r.ok) return;\n"
    "    return r.json();\n"
    "  }).then(function(d) {\n"
    "    if (d) renderStatus(d);\n"
    "  }).catch(function() {});\n"
    "}\n"
    "\n"
    "function sendDirective() {\n"
    "  var text = document.getElementById('dirText').value.trim();\n"
    "  if (!text) { showFeedback('dirFeedback', 'Text required', false); return; }\n"
    "  fetch(API + '/directive', {\n"
    "    method: 'POST',\n"
    "    headers: {'Content-Type': 'application/json'},\n"
    "    body: JSON.stringify({\n"
    "      text: text,\n"
    "      priority: document.getElementById('dirPriority').value,\n"
    "      ttl_ticks: parseInt(document.getElementById('dirTTL').value) || 10\n"
    "    })\n"
    "  }).then(function(r) { return r.json(); }).then(function(d) {\n"
    "    showFeedback('dirFeedback', d.message || 'OK', true);\n"
    "    document.getElementById('dirText').value = '';\n"
    "  }).catch(function(e) {\n"
    "    showFeedback('dirFeedback', 'Request failed: ' + e, false);\n"
    "  });\n"
    "}\n"
    "\n"
    "function sendOverride() {\n"
    "  var raw = document.getElementById('overrideJSON').value.trim();\n"
    "  if (!raw) { showFeedback('ovrFeedback', 'JSON required', false); return; }\n"
    "  var parsed;\n"
    "  try { parsed = JSON.parse(raw); } catch(e) {\n"
    "    showFeedback('ovrFeedback', 'Invalid JSON: ' + e.message, false); return;\n"
    "  }\n"
    "  fetch(API + '/override', {\n"
    "    method: 'POST',\n"
    "    headers: {'Content-Type': 'application/json'},\n"
    "    body: JSON.stringify({ commands: Array.isArray(parsed) ? parsed : [parsed] })\n"
    "  }).then(function(r) { return r.json(); }).then(function(d) {\n"
    "    showFeedback('ovrFeedback', d.message || 'OK', true);\n"
    "    document.getElementById('overrideJSON').value = '';\n"
    "  }).catch(function(e) {\n"
    "    showFeedback('ovrFeedback', 'Request failed: ' + e, false);\n"
    "  });\n"
    "}\n"
    "\n"
    "function sendControl(action) {\n"
    "  fetch(API + '/control', {\n"
    "    method: 'POST',\n"
    "    headers: {'Content-Type': 'application/json'},\n"
    "    body: JSON.stringify({ action: action })\n"
    "  }).then(function(r) { return r.json(); }).then(function(d) {\n"
    "    showFeedback('ctrlFeedback', d.message || 'OK', true);\n"
    "    refresh();\n"
    "  }).catch(function(e) {\n"
    "    showFeedback('ctrlFeedback', 'Request failed: ' + e, false);\n"
    "  });\n"
    "}\n"
    "\n"
    "// Auto-refresh every 3 seconds\n"
    "setInterval(refresh, 3000);\n"
    "refresh();\n"
    "</script>\n"
    "</body>\n"
    "</html>\n"
)
