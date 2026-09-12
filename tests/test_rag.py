"""
Unit Tests for Hybrid RAG Retrieval and Indexing.
"""
import unittest
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.rag.indexer import PolicyIndexer
from src.rag.hybrid_retriever import HybridRetriever

class TestHybridRAG(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.indexer = PolicyIndexer()
        cls.retriever = HybridRetriever(cls.indexer)

    def test_indexer_loads_policies(self):
        self.assertGreater(len(self.indexer.chunks), 0, "Indexer should have parsed internal policy chunks.")

    def test_retrieval_ai_governance(self):
        results = self.retriever.retrieve("vendor model training and customer data usage", top_k=2)
        self.assertGreater(len(results), 0)
        top_cat = results[0]["category"]
        self.assertEqual(top_cat, "AI_Governance", f"Expected AI_Governance, got {top_cat}")

    def test_retrieval_encryption(self):
        results = self.retriever.retrieve("AES-256 data at rest and TLS 1.3 in transit", top_k=2)
        self.assertGreater(len(results), 0)
        top_cat = results[0]["category"]
        self.assertEqual(top_cat, "Encryption", f"Expected Encryption, got {top_cat}")

    def test_retrieval_data_retention(self):
        results = self.retriever.retrieve("contract termination 30 days data deletion", top_k=2)
        self.assertGreater(len(results), 0)
        top_cat = results[0]["category"]
        self.assertEqual(top_cat, "Data_Retention", f"Expected Data_Retention, got {top_cat}")

if __name__ == "__main__":
    unittest.main()
