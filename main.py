import argparse
import json
from core import (
    ToolOperator, Runtime, SystemState, IntentSpace, 
    ExecutionGraphSpace, ArtifactSpace, HistorySpace
)

# Define some primitive tools
def write_file_tool(inputs):
    filename = inputs.get("filename", "output.txt")
    content = inputs.get("content", "Hello, Hilbert Space!")
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

tools = [
    ToolOperator(name="write_file", func=write_file_tool),
    ToolOperator(name="read_file", func=read_file_tool)
]

def run_demo():
    print("=== Hilbert-Space IDE Minimal Runtime Demo ===")
    
    # Initialize runtime
    runtime = Runtime(tools)
    
    # 1. First step: Write a file
    print("\n[Step 1] Intent: 'write a file'")
    context1 = {"filename": "demo.txt", "content": "Deterministic execution is beautiful."}
    state1 = runtime.step("write a file", context1)
    
    hash1 = state1.last_hash
    print(f"State Hash: {hash1}")
    print(f"Artifacts: {state1.A.artifacts}")
    
    # 2. Second step: Read the file
    print("\n[Step 2] Intent: 'read the file'")
    context2 = {"filename": "demo.txt"}
    state2 = runtime.step("read the file", context2)
    
    hash2 = state2.last_hash
    print(f"State Hash: {hash2}")
    print(f"Artifacts: {state2.A.artifacts}")
    
    # 3. Demonstrate Replay
    print("\n[Demonstrating Replay Operator R]")
    print(f"Replaying state hash: {hash1}")
    
    replayed_state = runtime.replay(hash1)
    
    print("\nReplayed State vs Original State 1:")
    print(f"Original Intent: {state1.I.raw_intent} | Replayed Intent: {replayed_state.I.raw_intent}")
    print(f"Original Graph: {state1.G.serialize()} | Replayed Graph: {replayed_state.G.serialize()}")
    print(f"Original Artifacts: {state1.A.artifacts} | Replayed Artifacts: {replayed_state.A.artifacts}")
    
    # Verify exact equality
    is_equal = (
        state1.I.raw_intent == replayed_state.I.raw_intent and
        state1.G.serialize() == replayed_state.G.serialize() and
        state1.A.artifacts == replayed_state.A.artifacts
    )
    
    print(f"\nExact equality under replay: {is_equal}")
    
    # 4. Demonstrate Trace Functional
    print("\n[Demonstrating Trace Functional tau]")
    trace = runtime.tau(state2)
    print(json.dumps(trace, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hilbert-Space IDE CLI")
    parser.add_argument("--intent", type=str, help="Intent to execute")
    parser.add_argument("--context", type=str, help="JSON context for execution")
    parser.add_argument("--demo", action="store_true", help="Run the full demo pipeline")
    
    args = parser.parse_args()
    
    if args.demo:
        run_demo()
    elif args.intent:
        runtime = Runtime(tools)
        context = json.loads(args.context) if args.context else {}
        state = runtime.step(args.intent, context)
        print(json.dumps({
            "hash": state.last_hash,
            "artifacts": state.A.artifacts
        }, indent=2))
    else:
        parser.print_help()
