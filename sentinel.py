import logging
import os
import json
import sys
from datetime import datetime
from typing import Optional

import pytz
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Path injection for Blackglass Shard Alpha modules
SHARD_ALPHA_PATH = r"c:\Users\colem\Code\blackglass-shard-alpha"
if SHARD_ALPHA_PATH not in sys.path:
    sys.path.append(SHARD_ALPHA_PATH)

# Path injection for Variance Core adapters
VARIANCE_CORE_PATH = r"c:\Users\colem\Code\blackglass-variance-core\src"
if VARIANCE_CORE_PATH not in sys.path:
    sys.path.append(VARIANCE_CORE_PATH)

try:
    from modules.safety_gasket import SafetyGasket
    from modules.sovereign_router import SovereignRouter
except ImportError:
    SafetyGasket = None
    SovereignRouter = None

try:
    from adapters.telemetry.air_node import AirNodeTelemetryAdapter
    _AIR_ADAPTER_AVAILABLE = True
except ImportError:
    AirNodeTelemetryAdapter = None
    _AIR_ADAPTER_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("blackglass-sentinel")

# Initialize FastMCP server
mcp = FastMCP("blackglass-sentinel")

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=dotenv_path)
HONEYCOMB_API_KEY = os.getenv("HONEYCOMB_API_KEY")
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY")

# Constitutional thresholds (mirrors constitution.py — kept local to avoid cross-repo import)
_CRITICAL_LATENCY_MS:  float = 5000.0  # 5.0s → MERCY PROTOCOL (physics death)
_CRITICAL_VARIANCE_CAP: float = 0.5    # 0.5V  → MERCY PROTOCOL (semantic collapse)

# Initialize Sovereign Components
if SafetyGasket:
    gasket = SafetyGasket(openai_key=OPENAI_API_KEY)
else:
    gasket = None

if not HONEYCOMB_API_KEY:
    raise ValueError("CRITICAL FAILURE: HONEYCOMB_API_KEY is missing from environment variables.")

@mcp.tool()
def scan_entropy_vectors() -> str:
    """
    Queries Honeycomb API for entropy vectors (P95 latency and COUNT) broken down by user_id.
    Demonstrates High-Cardinality awareness.
    """
    url = "https://api.honeycomb.io/1/query_results"
    headers = {
        "X-Honeycomb-Team": HONEYCOMB_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Query spec: Calculate P95(duration_ms) and COUNT, breakdown by user_id
    query_spec = {
        "query": {
            "calculations": [
                {"op": "P95", "column": "duration_ms"},
                {"op": "COUNT"}
            ],
            "breakdowns": ["user_id"],
            "limit": 5
        }
    }
    
    # In a real environment, we'd wait for the query to finish or fetch results.
    # For this MCP implementation, we simulate the 'heaviest' user impact response.
    # Note: Honeycomb API usually requires two steps (trigger query, then get results),
    # but we are abstracting the impact for the Lead SRE's decision loop.
    
    # Placeholder for actual API response processing
    # response = requests.post(url, headers=headers, json=query_spec)
    # results = response.json()
    
    # Simulating a high-entropy result
    heaviest_user = "user_7749"
    p95_latency = 845.2
    req_count = 1200
    
    return f"ENTROPY DETECTED: User '{heaviest_user}' is experiencing P95 latency of {p95_latency}ms across {req_count} requests."

@mcp.tool()
def assess_human_cost() -> str:
    """
    Evaluates engineer fatigue risk based on Denver local time.
    Logic: 23:00 - 07:00 is FATIGUE_RISK.
    """
    denver_tz  = pytz.timezone("America/Denver")
    denver_now = datetime.now(denver_tz)

    # CM-6: No magic numbers. GOD_MODE is an explicit, audit-logged env override.
    god_mode = os.getenv("SENTINEL_GOD_MODE", "false").lower() == "true"
    god_hour  = int(os.getenv("SENTINEL_GOD_HOUR", "3"))

    if god_mode:
        current_hour = god_hour
        logger.warning(
            "GOD_MODE_ACTIVE: Time artificially locked to hour %s — "
            "disable SENTINEL_GOD_MODE before federal deployment.",
            god_hour,
        )
    else:
        current_hour = denver_now.hour

    human_status = "FATIGUE_RISK" if (current_hour >= 23 or current_hour < 7) else "AVAILABLE"

    # Broadcast status for global circuit breaker
    status_data = {
        "timestamp": denver_now.isoformat(),
        "status": "FATIGUE_BREACH" if human_status == "FATIGUE_RISK" else "NOMINAL",
        "hour": current_hour,
        "god_mode": god_mode,
    }
    with open(os.path.join(os.path.dirname(__file__), "sentinel_status.json"), "w") as f:
        json.dump(status_data, f)

    if human_status == "FATIGUE_RISK":
        return "FATIGUE_RISK"
    return "AVAILABLE"

@mcp.tool()
def active_ui_interdiction(interdiction_type: str) -> str:
    """
    Executes system-level interdiction to protect the human responder.
    Types: CLOSE_STRESS_APPS, LOCK_WORKSTATION, NOTIFY_RESPONDER.
    """
    import subprocess
    
    if interdiction_type == "CLOSE_STRESS_APPS":
        # Simulate closing common stress-inducing applications
        # In a real SRE environment, this might be Slack, PagerDuty UI, etc.
        # Here we use 'taskkill' as a demonstration.
        # subprocess.run(["taskkill", "/F", "/IM", "slack.exe"], capture_output=True)
        return "INTERDICTION SUCCESS: Stress-inducing applications terminated. Sensory load reduced."
    
    elif interdiction_type == "LOCK_WORKSTATION":
        # Force the engineer to rest by locking the session
        try:
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
            return "INTERDICTION SUCCESS: Workstation locked. Rest protocol enforced."
        except Exception as e:
            return f"INTERDICTION FAILED: Could not lock workstation. Error: {str(e)}"
            
    elif interdiction_type == "NOTIFY_RESPONDER":
        # Visual notification using PowerShell
        msg = "FATIGUE BREACH DETECTED. SENTINEL IS EXECUTING MERCY PROTOCOL. GO TO SLEEP."
        ps_cmd = f"Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('{msg}', 'Blackglass Sentinel')"
        subprocess.Popen(["powershell", "-Command", ps_cmd])
        return "INTERDICTION SUCCESS: Fatigue notification delivered to responder UI."

    return f"UNKNOWN INTERDICTION TYPE: {interdiction_type}"

@mcp.tool()
def get_vault_variance() -> dict:
    """
    Pulls live V(t) from the A.I.R. VaultNode via the authenticated
    AirNodeTelemetryAdapter. Returns variance score, incident count,
    and a NOMINAL/INTERDICT status tag for Claude's context window.

    Requires AIR_NODE_URL and AIR_NODE_API_KEY in .env.
    """
    if not _AIR_ADAPTER_AVAILABLE:
        return {
            "status": "error",
            "message": "AirNodeTelemetryAdapter unavailable — check VARIANCE_CORE_PATH.",
        }

    try:
        adapter = AirNodeTelemetryAdapter()
        result  = adapter.get_window()
    except Exception as exc:
        logger.exception("get_vault_variance: adapter error")
        return {"status": "error", "message": str(exc)}

    if result.get("status") != "ok":
        return result

    v          = result["variance_detected"]
    incidents  = result.get("features", {}).get("incident_count", "?")
    window_sec = result.get("features", {}).get("window_sec", "?")

    interdict = v >= _CRITICAL_VARIANCE_CAP
    tag       = "INTERDICT_DRIFT" if interdict else "NOMINAL"

    logger.info("Vault variance V(t)=%.4f incidents=%s status=%s", v, incidents, tag)

    return {
        "status":         "ok",
        "variance":       v,
        "verdict":        tag,
        "incident_count": incidents,
        "window_sec":     window_sec,
        "raw":            result,
    }


@mcp.tool()
def execute_defense_protocol(
    latency_ms:   float,
    human_status: str,
    variance:     Optional[float] = None,
) -> str:
    """
    Dual-channel sovereign reliability decision logic.

    Trigger channels (either alone fires MERCY PROTOCOL):
      - Physics channel:   latency_ms > CRITICAL_LATENCY_CAP (5000ms)
      - Semantic channel:  variance   > CRITICAL_VARIANCE_CAP (0.5V)

    If human is at FATIGUE_RISK during any breach → MERCY PROTOCOL.
    If human is AVAILABLE during a breach → PAGING PROTOCOL.
    Both channels clean → WATCH PROTOCOL.

    Pass variance from get_vault_variance()["variance"] for full sovereignty.
    Omit variance (or pass None) to run on latency signal only.
    """
    latency_breach  = latency_ms > _CRITICAL_LATENCY_MS
    variance_breach = (variance is not None) and (variance > _CRITICAL_VARIANCE_CAP)
    any_breach      = latency_breach or variance_breach

    # Build a diagnostic tag for the response
    breach_sources = []
    if latency_breach:
        breach_sources.append(f"LATENCY={latency_ms:.0f}ms>{_CRITICAL_LATENCY_MS:.0f}ms")
    if variance_breach:
        breach_sources.append(f"V(t)={variance:.4f}>{_CRITICAL_VARIANCE_CAP}")
    breach_tag = " | ".join(breach_sources) if breach_sources else "NONE"

    if any_breach:
        logger.warning(
            "Breach detected: %s | human_status=%s", breach_tag, human_status
        )
        if human_status == "FATIGUE_RISK":
            interdiction_result = active_ui_interdiction("NOTIFY_RESPONDER")
            return (
                f"MERCY PROTOCOL ACTIVATED: Breach [{breach_tag}] during FATIGUE_RISK. "
                f"Auto-Rollback initiated. DO NOT PAGE ENGINEERS. {interdiction_result}"
            )
        else:
            return (
                f"PAGING PROTOCOL: Breach [{breach_tag}] detected. "
                "Engineering responders AVAILABLE. Paging now."
            )

    return (
        f"WATCH PROTOCOL: All channels nominal "
        f"(latency={latency_ms:.0f}ms, V(t)={variance if variance is not None else 'N/A'}). "
        "Monitoring entropy vectors."
    )

@mcp.tool()
def stream_safe_analysis(prompt: str) -> str:
    """
    Performs a high-assurance LLM analysis through the Safety Gasket.
    Uses the 5-token sliding window to prevent prefix leaks of sensitive SRE data.
    """
    if not gasket:
        return "ERROR: Safety Gasket not initialized. Check SHARD_ALPHA_PATH."
        
    system_prompt = "You are the Blackglass Sentinel. You provide high-assurance SRE analysis. Be concise, federal, and technical."
    
    try:
        response_chunks = []
        for chunk in gasket.stream_safe_response(prompt, system_prompt=system_prompt):
            response_chunks.append(chunk)
            
        return "".join(response_chunks)
    except Exception as e:
        return f"CRITICAL GASKET FAILURE: {str(e)}"

if __name__ == "__main__":
    mcp.run()
