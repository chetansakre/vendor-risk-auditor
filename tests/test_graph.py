"""
Integration Tests for the LangGraph State Machine & Human-in-the-Loop Checkpoint.
"""
import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.utils.parser import parse_document
from src.graph.workflow import build_audit_graph

class TestLangGraphWorkflow(unittest.TestCase):
    def setUp(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.doc_path = os.path.join(base_dir, "data", "sample_vendors", "cloudsync_soc2_report.pdf")
        self.parsed = parse_document(self.doc_path)
        self.graph = build_audit_graph(enable_hitl=True)

    def test_end_to_end_audit_with_hitl(self):
        config = {"configurable": {"thread_id": "test-thread-audit-001"}}

        initial_state = {
            "vendor_name": "CloudSync AI",
            "document_path": self.doc_path,
            "document_text": self.parsed["full_text"],
            "sections": self.parsed["sections"],
            "extracted_clauses": [],
            "retrieved_policies": {},
            "checklist": [],
            "reflection_notes": [],
            "scorecard": {},
            "human_approved": False,
            "human_reviewer": "",
            "human_feedback": "",
            "mcp_actions_taken": [],
            "current_step": "Initialized"
        }

        # Step 1: Run graph up to the breakpoint
        for _ in self.graph.stream(initial_state, config=config):
            pass

        snapshot = self.graph.get_state(config)
        self.assertIn("execute_mcp", snapshot.next, "Graph should pause right before execute_mcp for human approval.")

        scorecard = snapshot.values.get("scorecard", {})
        self.assertEqual(scorecard.get("overall_risk"), "HIGH", "CloudSync should be flagged as HIGH risk due to AI training and 90-day retention.")
        self.assertGreater(scorecard.get("fail_count", 0), 1)

        # Step 2: Simulate Human Reviewer Sign-off & Resume Graph
        self.graph.update_state(config, {
            "human_approved": True,
            "human_reviewer": "Lead Security Auditor",
            "human_feedback": "Approved with mandatory requirement for custom legal rider."
        })

        for _ in self.graph.stream(None, config=config):
            pass

        final_snapshot = self.graph.get_state(config)
        actions = final_snapshot.values.get("mcp_actions_taken", [])
        self.assertEqual(len(actions), 3, "All 3 MCP tools should have been invoked after approval.")

if __name__ == "__main__":
    unittest.main()
