"""
LangGraph Workflow Orchestrator
Builds the cyclic state graph with state persistence and Human-in-the-Loop checkpoints.
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from .state import RiskAuditState
from .nodes import (
    extract_clauses_node,
    retrieve_policies_node,
    audit_compliance_node,
    reflection_verifier_node,
    compile_scorecard_node,
    execute_mcp_node
)

def build_audit_graph(enable_hitl: bool = True):
    """
    Compiles and returns the LangGraph workflow.
    If enable_hitl is True, sets interrupt_before=['execute_mcp']
    allowing security engineers to review and approve before any tool executes.
    """
    builder = StateGraph(RiskAuditState)

    # Add Nodes
    builder.add_node("extract_clauses", extract_clauses_node)
    builder.add_node("retrieve_policies", retrieve_policies_node)
    builder.add_node("audit_compliance", audit_compliance_node)
    builder.add_node("reflection_verifier", reflection_verifier_node)
    builder.add_node("compile_scorecard", compile_scorecard_node)
    builder.add_node("execute_mcp", execute_mcp_node)

    # Set Linear / Cyclic Edges
    builder.set_entry_point("extract_clauses")
    builder.add_edge("extract_clauses", "retrieve_policies")
    builder.add_edge("retrieve_policies", "audit_compliance")
    builder.add_edge("audit_compliance", "reflection_verifier")
    builder.add_edge("reflection_verifier", "compile_scorecard")
    builder.add_edge("compile_scorecard", "execute_mcp")
    builder.add_edge("execute_mcp", END)

    # Setup Checkpointer
    checkpointer = MemorySaver()

    if enable_hitl:
        graph = builder.compile(
            checkpointer=checkpointer,
            interrupt_before=["execute_mcp"]
        )
    else:
        graph = builder.compile(checkpointer=checkpointer)

    return graph
