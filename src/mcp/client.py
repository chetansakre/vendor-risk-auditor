"""
MCP Client
Launches and manages connection to the MCP Server over stdio.
Allows the LangGraph agent to discover and invoke tools seamlessly.
"""
import sys
import json
import os
import subprocess
from typing import List, Dict, Any

class MCPClient:
    def __init__(self, server_script: str = None):
        if server_script is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            server_script = os.path.join(base_dir, "server.py")
        self.server_script = server_script
        self.proc = None
        self._msg_id = 0
        self.tools = []
        self._start_server()

    def _start_server(self):
        python_exe = sys.executable
        self.proc = subprocess.Popen(
            [python_exe, self.server_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        # Initialize handshake
        self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "langgraph-auditor-agent", "version": "1.0.0"}
        })
        # Discover tools
        tools_resp = self._send_request("tools/list", {})
        if tools_resp and "result" in tools_resp and "tools" in tools_resp["result"]:
            self.tools = tools_resp["result"]["tools"]

    def _send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        self._msg_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._msg_id,
            "method": method,
            "params": params
        }
        if self.proc and self.proc.stdin:
            self.proc.stdin.write(json.dumps(payload) + "\n")
            self.proc.stdin.flush()
            response_line = self.proc.stdout.readline()
            if response_line:
                return json.loads(response_line.strip())
        return {}

    def list_tools(self) -> List[Dict[str, Any]]:
        return self.tools

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        resp = self._send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })
        if "result" in resp:
            content = resp["result"].get("content", [])
            if content and content[0].get("type") == "text":
                return json.loads(content[0]["text"])
            return resp["result"]
        elif "error" in resp:
            return {"status": "error", "error": resp["error"]}
        return {"status": "error", "error": "Unknown response from MCP server"}

    def close(self):
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=2)
            except Exception:
                pass
