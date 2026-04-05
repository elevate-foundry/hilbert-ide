#!/usr/bin/env python3
"""
Hilbert-Space IDE: CLI Interface
Section 9 of the spec: CLI -> deterministic invocation of operators
"""
import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
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

# Persistent runtime (in-memory for demo; could be backed by a file)
runtime = Runtime(TOOLS)

def cmd_step(args):
    """Execute a single system evolution step"""
    context = json.loads(args.context) if args.context else {}
    state = runtime.step(args.intent, context)
    
    print(f"\n[State Hash]  {state.last_hash}")
    print(f"[Intent]      {state.I.raw_intent}")
    print(f"[Graph]       {json.dumps(state.G.serialize(), indent=2)}")
    print(f"[Artifacts]   {json.dumps(state.A.artifacts, indent=2)}")
    print(f"[Ledger Size] {len(state.H.ledger)} records")

def cmd_replay(args):
    """Replay a committed state by hash"""
    try:
        state = runtime.replay(args.hash)
        print(f"\n[Replayed State for Hash: {args.hash}]")
        print(f"[Intent]    {state.I.raw_intent}")
        print(f"[Graph]     {json.dumps(state.G.serialize(), indent=2)}")
        print(f"[Artifacts] {json.dumps(state.A.artifacts, indent=2)}")
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

def cmd_trace(args):
    """Get the audit trace for the current state"""
    trace = runtime.tau(runtime.state)
    print(json.dumps(trace, indent=2))

def cmd_history(args):
    """Print the full append-only ledger"""
    ledger = runtime.state.H.ledger
    if not ledger:
        print("[History is empty]")
        return
    for i, record in enumerate(ledger):
        print(f"\n[Record {i+1}]")
        print(f"  Hash:      {record['hash']}")
        print(f"  Intent:    {record['I']['raw']}")
        print(f"  Operators: {record['G']['operators']}")
        print(f"  Artifacts: {list(record['A'].keys())}")

def cmd_tools(args):
    """List available primitive operators"""
    print("\n[Tool Algebra T = {T_1, ..., T_n}]")
    for t in TOOLS:
        print(f"  - {t.name}")

def cmd_demo(args):
    """Run the full demo pipeline demonstrating I -> G -> A -> H -> (I,G,A)"""
    print("=== Hilbert-Space IDE: Full Pipeline Demo ===")
    print("\nDemonstrating: I --P--> G --E--> A --C--> H --R--> (I,G,A)")
    
    # Step 1: Write
    print("\n[1] Intent: 'write a file'")
    ctx1 = {"filename": "demo.txt", "content": "Deterministic execution is beautiful."}
    s1 = runtime.step("write a file", ctx1)
    h1 = s1.last_hash
    print(f"    Hash: {h1}")
    print(f"    Artifacts: {s1.A.artifacts}")
    
    # Step 2: Read
    print("\n[2] Intent: 'read the file'")
    ctx2 = {"filename": "demo.txt"}
    s2 = runtime.step("read the file", ctx2)
    h2 = s2.last_hash
    print(f"    Hash: {h2}")
    print(f"    Artifacts: {s2.A.artifacts}")
    
    # Replay step 1
    print(f"\n[3] Replay of step 1 (hash: {h1})")
    replayed = runtime.replay(h1)
    exact = (
        replayed.I.raw_intent == s1.I.raw_intent and
        replayed.G.serialize() == s1.G.serialize() and
        replayed.A.artifacts == s1.A.artifacts
    )
    print(f"    Intent match:    {replayed.I.raw_intent == s1.I.raw_intent}")
    print(f"    Graph match:     {replayed.G.serialize() == s1.G.serialize()}")
    print(f"    Artifact match:  {replayed.A.artifacts == s1.A.artifacts}")
    print(f"    Exact equality:  {exact}")
    
    # Trace
    print("\n[4] Audit trace for current state:")
    trace = runtime.tau(runtime.state)
    print(json.dumps(trace, indent=4))
    
    print("\n=== Demo Complete ===")

def main():
    parser = argparse.ArgumentParser(
        prog="hilbert-ide",
        description="Hilbert-Space AI-Native IDE: Deterministic execution over H = H_I ⊕ H_G ⊕ H_A ⊕ H_H"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # step
    p_step = subparsers.add_parser("step", help="Execute a system evolution step")
    p_step.add_argument("intent", type=str, help="Natural language intent")
    p_step.add_argument("--context", type=str, default=None, help="JSON context dict")
    p_step.set_defaults(func=cmd_step)
    
    # replay
    p_replay = subparsers.add_parser("replay", help="Replay a committed state by hash")
    p_replay.add_argument("hash", type=str, help="SHA-256 state hash")
    p_replay.set_defaults(func=cmd_replay)
    
    # trace
    p_trace = subparsers.add_parser("trace", help="Get audit trace for current state")
    p_trace.set_defaults(func=cmd_trace)
    
    # history
    p_history = subparsers.add_parser("history", help="Print the append-only ledger")
    p_history.set_defaults(func=cmd_history)
    
    # tools
    p_tools = subparsers.add_parser("tools", help="List available primitive operators")
    p_tools.set_defaults(func=cmd_tools)
    
    # demo
    p_demo = subparsers.add_parser("demo", help="Run the full demo pipeline")
    p_demo.set_defaults(func=cmd_demo)
    
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
