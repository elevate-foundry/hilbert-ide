"""
Hilbert-Space IDE: REST API Interface
Section 9 of the spec: API -> direct access to H
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import json

from core import ToolOperator, Runtime

# --- Tool definitions ---
def write_file_tool(inputs):
    filename = inputs.get("filename", "output.txt")
    content = inputs.get("content", "")
    with open(filename, "w") as f:
        f.write(content)
    return {"written_file": filename, "status": "success"}

def read_file_tool(inputs):
    filename = inputs.get("filename", "output.txt")
    try:
        with open(filename, "r") as f:
            content = f.read()
        return {"read_content": content, "status": "success"}
    except FileNotFoundError:
        return {"error": "File not found", "status": "failed"}

TOOLS = [
    ToolOperator(name="write_file", func=write_file_tool),
    ToolOperator(name="read_file", func=read_file_tool),
]

# --- Shared runtime instance ---
runtime = Runtime(TOOLS)

# --- FastAPI app ---
app = FastAPI(
    title="Hilbert-Space IDE API",
    description="Minimal runtime realizing deterministic operator composition over H = H_I ⊕ H_G ⊕ H_A ⊕ H_H",
    version="0.1.0"
)

# --- Request/Response models ---
class StepRequest(BaseModel):
    intent: str
    context: Optional[Dict[str, Any]] = {}

class StepResponse(BaseModel):
    hash: str
    intent: str
    graph: Dict[str, Any]
    artifacts: Dict[str, Any]

class ReplayResponse(BaseModel):
    hash: str
    intent: str
    graph: Dict[str, Any]
    artifacts: Dict[str, Any]

class TraceResponse(BaseModel):
    intent: str
    operations: List[str]
    artifacts_produced: List[str]
    state_hash: str

# --- Routes ---
@app.post("/step", response_model=StepResponse, summary="Execute a single system evolution step")
def step(req: StepRequest):
    """
    Executes: s_{t+1} = (I, P(I), E(P(I)), C(I, P(I), E(P(I))))
    """
    state = runtime.step(req.intent, req.context)
    return StepResponse(
        hash=state.last_hash,
        intent=state.I.raw_intent,
        graph=state.G.serialize(),
        artifacts=state.A.artifacts
    )

@app.get("/replay/{target_hash}", response_model=ReplayResponse, summary="Replay a committed state by hash")
def replay(target_hash: str):
    """
    Executes: R(C(s)) = s  (exact equality under replay)
    """
    try:
        state = runtime.replay(target_hash)
        return ReplayResponse(
            hash=target_hash,
            intent=state.I.raw_intent,
            graph=state.G.serialize(),
            artifacts=state.A.artifacts
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/trace", response_model=TraceResponse, summary="Get audit trace for current state")
def trace():
    """
    Executes: tau: H -> R^k (explanation)
    """
    t = runtime.tau(runtime.state)
    return TraceResponse(
        intent=t["intent"],
        operations=t["operations"],
        artifacts_produced=t["artifacts_produced"],
        state_hash=t["state_hash"]
    )

@app.get("/history", summary="Get full append-only ledger")
def history():
    """Returns the full immutable, append-only history ledger H_H"""
    return {"ledger": runtime.state.H.ledger}

@app.get("/tools", summary="List available primitive operators T")
def list_tools():
    """Returns the tool algebra T = {T_1, ..., T_n}"""
    return {"tools": [t.name for t in TOOLS]}

@app.get("/state", summary="Get current system state summary")
def state():
    """Returns a summary of the current system state s = (I, G, A, H)"""
    s = runtime.state
    return {
        "I": {"raw_intent": s.I.raw_intent},
        "G": s.G.serialize(),
        "A": s.A.artifacts,
        "H": {"ledger_length": len(s.H.ledger)}
    }
