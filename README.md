# Hilbert-Space AI-Native IDE: Minimal Runtime

A minimal runtime realizing a deterministic execution system formalized over a separable Hilbert space, as specified in the Hilbert-Space Formulation builder prompt.

---

## Architecture

The total system space is defined as:

```
H = H_I ⊕ H_G ⊕ H_A ⊕ H_H
```

The system state at any time is the tuple:

```
s = (I, G, A, H)
```

| Component | Space | Description |
|-----------|-------|-------------|
| `I` | `H_I` | Intent embedding space |
| `G` | `H_G` | Execution graph space |
| `A` | `H_A` | Artifact space |
| `H` | `H_H` | History (ledger) space |

---

## Operators

| Operator | Signature | Description |
|----------|-----------|-------------|
| `P` (Planning) | `H_I → H_G` | Maps intent to execution graph |
| `E` (Execution) | `H_G → H_A` | Executes graph, produces artifacts |
| `C` (Commit) | `H_I ⊕ H_G ⊕ H_A → H_H` | Projects state into ledger |
| `R` (Replay) | `H_H → H` | Reconstructs state from ledger |
| `S` (Compression) | `H_I → H_G` | Semantic compression of intent |
| `τ` (Trace) | `H → R^k` | Audit trace functional |

System evolution:

```
s_{t+1} = (I, P(I), E(P(I)), C(I, P(I), E(P(I))))
```

---

## Files

| File | Description |
|------|-------------|
| `core.py` | Core runtime: all spaces, operators, and `Runtime` class |
| `cli.py` | CLI interface (deterministic invocation of operators) |
| `api.py` | REST API interface (direct access to H via FastAPI) |
| `main.py` | Standalone demo script |
| `test_runtime.py` | Full test suite (23 tests, all passing) |

---

## Quick Start

### CLI

```bash
# Run the full demo pipeline
python3 cli.py demo

# Execute a step
python3 cli.py step "write a file" --context '{"filename":"out.txt","content":"hello"}'

# Replay a committed state by hash
python3 cli.py replay <sha256-hash>

# Get audit trace
python3 cli.py trace

# View full ledger
python3 cli.py history

# List available operators
python3 cli.py tools
```

### REST API

```bash
# Start the server
uvicorn api:app --host 0.0.0.0 --port 8765

# Execute a step
curl -X POST http://localhost:8765/step \
  -H "Content-Type: application/json" \
  -d '{"intent":"write a file","context":{"filename":"out.txt","content":"hello"}}'

# Replay a state
curl http://localhost:8765/replay/<sha256-hash>

# Get audit trace
curl http://localhost:8765/trace

# View ledger
curl http://localhost:8765/history

# List tools
curl http://localhost:8765/tools

# Current state summary
curl http://localhost:8765/state
```

### API Docs

When the server is running, visit `http://localhost:8765/docs` for the interactive Swagger UI.

---

## Replay Guarantee

The system demonstrates exact equality under replay:

```
R(C(s)) = s
```

That is, for any committed state `s` with hash `h`:
- `R(h).I.raw_intent == s.I.raw_intent`
- `R(h).G.serialize() == s.G.serialize()`
- `R(h).A.artifacts == s.A.artifacts`

This is verified by the test suite on every run.

---

## Test Suite

```bash
python3 test_runtime.py
```

All 23 tests cover:
- Section 1: State space structure
- Section 2: Determinism and reproducibility
- Section 3: Tool algebra
- Section 4: Execution graph serialization
- Section 5: Commit/replay (R(C(s)) = s)
- Section 7: Audit trace functional
- Section 8: Semantic compression
- Section 10: Constraint enforcement

---

## Extending the Tool Algebra

Add new primitive operators by defining a function and wrapping it in `ToolOperator`:

```python
def my_tool(inputs: dict) -> dict:
    # ... deterministic computation ...
    return {"result": ...}

from core import ToolOperator
my_op = ToolOperator(name="my_tool", func=my_tool)
```

Register it with the `Runtime`:

```python
runtime = Runtime([..., my_op])
```

The planning operator will automatically route intents containing the tool's name.
