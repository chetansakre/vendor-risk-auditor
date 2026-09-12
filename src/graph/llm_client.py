"""
Private Qwen 122B Enterprise Inference Client
Connects to self-hosted vLLM/SGLang/OpenAI-compatible server with graceful fallback.
"""
import os
import json
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()

class QwenLLMClient:
    def __init__(self, base_url=None, api_key=None, model=None):
        self.base_url = (base_url or os.getenv("QWEN_BASE_URL", "http://47.29.24.146:8002/v1")).rstrip("/")
        self.api_key = api_key or os.getenv("QWEN_API_KEY", "")
        self.model = model or os.getenv("QWEN_MODEL_NAME", "qwen-122b")

    def test_connection(self) -> dict:
        """Checks if the Qwen 122B server is online and reachable."""
        try:
            req = urllib.request.Request(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m.get("id") for m in data.get("data", [])]
                return {"online": True, "models": models}
        except Exception as e:
            return {"online": False, "error": str(e)}

    def audit_clause_with_qwen(self, category: str, policy_standard: str, vendor_evidence: str) -> dict:
        """
        Sends vendor evidence and policy requirement to Qwen 122B for frontier legal reasoning.
        """
        prompt = f"""You are a Lead Enterprise Cybersecurity & Vendor Risk Auditor.
Evaluate the following vendor evidence against our mandatory enterprise security standard.

[MANDATORY ENTERPRISE POLICY STANDARD]
Category: {category}
Requirement: {policy_standard}

[VENDOR EVIDENCE SNIPPET]
{vendor_evidence}

Respond strictly with a single valid JSON object in this exact schema (no additional markdown or conversational text):
{{
    "status": "PASS",
    "confidence": 0.95,
    "reasoning": "1-2 sentence legal assessment explaining the finding."
}}
Valid values for status are: PASS, FAIL, NEEDS_REVIEW.
"""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a strict enterprise compliance auditor. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 1000
        }

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
        )

        try:
            import re
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                raw_text = body["choices"][0]["message"]["content"].strip()
                
                # Check for explicit json code blocks
                if "```json" in raw_text:
                    block = raw_text.split("```json")[1].split("```")[0].strip()
                    try:
                        return json.loads(block)
                    except Exception:
                        pass
                
                # Search for JSON object with "status" key
                matches = re.findall(r'\{[^{}]*"status"[^{}]*\}', raw_text, re.DOTALL)
                if matches:
                    return json.loads(matches[-1])

                # Fallback: search for first { to }
                m = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if m:
                    return json.loads(m.group(0))

                return {"error": "No valid JSON found in model output", "raw": raw_text[:200]}
        except Exception as e:
            return {"error": str(e)}
