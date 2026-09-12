"""
Integration Tests for Model Context Protocol (MCP) Server and Client.
"""
import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.mcp.client import MCPClient

class TestMCPIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = MCPClient()

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def test_mcp_tool_discovery(self):
        tools = self.client.list_tools()
        tool_names = [t["name"] for t in tools]
        self.assertIn("save_audit_report", tool_names)
        self.assertIn("create_compliance_ticket", tool_names)
        self.assertIn("send_slack_alert", tool_names)

    def test_mcp_call_save_report(self):
        res = self.client.call_tool("save_audit_report", {
            "vendor_name": "UnitTestVendor",
            "risk_score": "LOW",
            "markdown_content": "# Unit Test Audit Report\nAll tests passed."
        })
        self.assertEqual(res.get("status"), "success")
        self.assertTrue(os.path.exists(res.get("file_path")))

    def test_mcp_call_create_ticket(self):
        res = self.client.call_tool("create_compliance_ticket", {
            "vendor_name": "UnitTestVendor",
            "summary": "Compliance Review for UnitTestVendor",
            "priority": "P2",
            "flagged_issues": ["Retention policy > 30 days"]
        })
        self.assertEqual(res.get("status"), "created")
        self.assertTrue(res.get("ticket_id", "").startswith("SEC-"))

if __name__ == "__main__":
    unittest.main()