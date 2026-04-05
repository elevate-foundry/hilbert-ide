import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, TypeVar, Generic

# 1) State space (Hilbert Space formulation)
# s = (I, G, A, H)

@dataclass(frozen=True)
class IntentSpace:
    """H_I: Intent embedding space"""
    embedding: List[float]
    raw_intent: str

@dataclass(frozen=True)
class ArtifactSpace:
    """H_A: Artifact space"""
    artifacts: Dict[str, Any]

@dataclass(frozen=True)
class HistorySpace:
    """H_H: History (ledger) space"""
    ledger: List[Dict[str, Any]]

# 3) Tool algebra (operator basis)
@dataclass(frozen=True)
class ToolOperator:
    """T_i: Primitive operator"""
    name: str
    func: Any # Callable[[Dict[str, Any]], Dict[str, Any]]
    
    def __call__(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return self.func(inputs)

@dataclass(frozen=True)
class ExecutionGraphSpace:
    """H_G: Execution graph space (Composition of operators)"""
    operators: List[ToolOperator]
    data_dependencies: Dict[str, str] # Maps output keys to input keys
    
    def serialize(self) -> Dict[str, Any]:
        return {
            "operators": [op.name for op in self.operators],
            "dependencies": self.data_dependencies
        }

@dataclass(frozen=True)
class SystemState:
    """s = (I, G, A, H)"""
    I: IntentSpace
    G: ExecutionGraphSpace
    A: ArtifactSpace
    H: HistorySpace

    def hash(self) -> str:
        """Content-addressable identity"""
        state_dict = {
            "I": {"raw": self.I.raw_intent, "emb": self.I.embedding},
            "G": self.G.serialize(),
            "A": self.A.artifacts,
            "H": len(self.H.ledger) # Simplified for demo
        }
        state_str = json.dumps(state_dict, sort_keys=True)
        return hashlib.sha256(state_str.encode()).hexdigest()

# 2) Deterministic operators
class PlanningOperator:
    """P: H_I -> H_G"""
    def __init__(self, available_tools: List[ToolOperator]):
        self.tools = {t.name: t for t in available_tools}
        
    def __call__(self, intent: IntentSpace) -> ExecutionGraphSpace:
        # Dummy deterministic planning based on intent string
        if "write" in intent.raw_intent.lower():
            return ExecutionGraphSpace(
                operators=[self.tools["write_file"]],
                data_dependencies={}
            )
        elif "read" in intent.raw_intent.lower():
            return ExecutionGraphSpace(
                operators=[self.tools["read_file"]],
                data_dependencies={}
            )
        else:
            return ExecutionGraphSpace(operators=[], data_dependencies={})

class ExecutionOperator:
    """E: H_G -> H_A"""
    def __call__(self, graph: ExecutionGraphSpace, initial_context: Dict[str, Any] = None) -> ArtifactSpace:
        context = initial_context or {}
        artifacts = {}
        
        # 4) Execution graph as operator composition
        # E = T_k o T_{k-1} o ... o T_1
        for op in graph.operators:
            # Resolve dependencies (simplified)
            inputs = context.copy()
            outputs = op(inputs)
            artifacts.update(outputs)
            context.update(outputs)
            
        return ArtifactSpace(artifacts=artifacts)

class CommitOperator:
    """C: H_I x H_G x H_A -> H_H"""
    def __call__(self, I: IntentSpace, G: ExecutionGraphSpace, A: ArtifactSpace, current_H: HistorySpace) -> HistorySpace:
        # 5) History as projection
        # C(s) = Pi_H(s)
        
        # Create a temporary state to hash
        # Note: The hash should be based on the state *after* the commit, 
        # but since H is part of the state, we need to be careful.
        # For simplicity, we hash the state *before* adding the new record to the ledger.
        temp_state = SystemState(I=I, G=G, A=A, H=current_H)
        state_hash = temp_state.hash()
        
        record = {
            "hash": state_hash,
            "I": {"raw": I.raw_intent, "emb": I.embedding},
            "G": G.serialize(),
            "A": A.artifacts
        }
        
        new_ledger = current_H.ledger.copy()
        new_ledger.append(record)
        return HistorySpace(ledger=new_ledger)

class ReplayOperator:
    """R: H_H -> H"""
    def __init__(self, available_tools: List[ToolOperator]):
        self.tools = {t.name: t for t in available_tools}
        
    def __call__(self, history: HistorySpace, target_hash: str) -> SystemState:
        record = next((r for r in history.ledger if r["hash"] == target_hash), None)
        if not record:
            raise ValueError(f"Hash {target_hash} not found in history")
            
        I = IntentSpace(raw_intent=record["I"]["raw"], embedding=record["I"]["emb"])
        
        # Reconstruct G
        ops = [self.tools[name] for name in record["G"]["operators"]]
        G = ExecutionGraphSpace(operators=ops, data_dependencies=record["G"]["dependencies"])
        
        A = ArtifactSpace(artifacts=record["A"])
        
        # Reconstruct state up to that point
        idx = history.ledger.index(record)
        H = HistorySpace(ledger=history.ledger[:idx+1])
        
        return SystemState(I=I, G=G, A=A, H=H)

# 8) Semantic compression
class CompressionOperator:
    """S: H_I -> H_G"""
    def __init__(self, planner: PlanningOperator):
        self.planner = planner
        
    def __call__(self, intent: IntentSpace) -> ExecutionGraphSpace:
        # S(I) -> G such that ||S(I)|| < ||I|| and E(S(I)) approx E(P(I))
        # In this minimal runtime, we just use the planner directly as a stub
        return self.planner(intent)

# 7) Compliance / auditability
class TraceFunctional:
    """tau: H -> R^k (Explanation)"""
    def __call__(self, state: SystemState) -> Dict[str, Any]:
        return {
            "intent": state.I.raw_intent,
            "operations": [op.name for op in state.G.operators],
            "artifacts_produced": list(state.A.artifacts.keys()),
            "state_hash": state.hash()
        }

# System Evolution
class Runtime:
    def __init__(self, tools: List[ToolOperator]):
        self.tools = tools
        self.P = PlanningOperator(tools)
        self.E = ExecutionOperator()
        self.C = CommitOperator()
        self.R = ReplayOperator(tools)
        self.tau = TraceFunctional()
        
        # Initial empty state
        self.state = SystemState(
            I=IntentSpace(embedding=[], raw_intent=""),
            G=ExecutionGraphSpace(operators=[], data_dependencies={}),
            A=ArtifactSpace(artifacts={}),
            H=HistorySpace(ledger=[])
        )
        
    def step(self, raw_intent: str, context: Dict[str, Any] = None) -> SystemState:
        """s_{t+1} = (I, P(I), E(P(I)), C(I, P(I), E(P(I))))"""
        # 1. New Intent
        I = IntentSpace(embedding=[0.0], raw_intent=raw_intent) # Dummy embedding
        
        # 2. Plan
        G = self.P(I)
        
        # 3. Execute
        A = self.E(G, context)
        
        # 4. Commit
        H = self.C(I, G, A, self.state.H)
        
        # Update system state
        # The state hash returned should match the hash recorded in the ledger
        # The commit operator hashes the state *before* adding the new record
        temp_state = SystemState(I=I, G=G, A=A, H=self.state.H)
        self.state = SystemState(I=I, G=G, A=A, H=H)
        
        # We attach the hash to the state dynamically for the demo
        object.__setattr__(self.state, 'last_hash', temp_state.hash())
        return self.state
        
    def replay(self, target_hash: str) -> SystemState:
        """Demonstrate R(C(s)) = s"""
        return self.R(self.state.H, target_hash)
