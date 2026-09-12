"""
Hybrid Policy Retriever
Combines BM25 keyword matching with dense vector search using Reciprocal Rank Fusion (RRF).
Applies domain-specific security keyword boosts for strict compliance checking.
"""
from typing import List, Dict, Any
from .indexer import PolicyIndexer, PolicyChunk

class HybridRetriever:
    def __init__(self, indexer: PolicyIndexer = None):
        if indexer is None:
            indexer = PolicyIndexer()
        self.indexer = indexer

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Performs hybrid retrieval using Reciprocal Rank Fusion (RRF).
        Returns list of matched policy chunks with relevance metadata.
        """
        bm25_results = self.indexer.search_bm25(query, top_k=top_k * 2)
        dense_results = self.indexer.search_dense(query, top_k=top_k * 2)

        rrf_scores = {}
        chunk_map = {}
        k = 60  # RRF constant

        # Process BM25 rankings
        for rank, (chunk, score) in enumerate(bm25_results):
            cid = chunk.policy_id
            chunk_map[cid] = chunk
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (k + rank + 1))

        # Process Dense rankings
        for rank, (chunk, score) in enumerate(dense_results):
            cid = chunk.policy_id
            chunk_map[cid] = chunk
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (k + rank + 1))

        # Security Domain Keyword Boost
        query_lower = query.lower()
        boost_keywords = {
            "aes-256": "Encryption",
            "tls 1.3": "Encryption",
            "model training": "AI_Governance",
            "retrain": "AI_Governance",
            "30 days": "Data_Retention",
            "retention": "Data_Retention",
            "subprocessor": "Subprocessors",
            "breach": "Incident_Response",
            "24 hours": "Incident_Response",
            "soc 2": "Audits_Certifications",
            "mfa": "Access_Control",
            "sso": "Access_Control"
        }

        for kw, target_cat in boost_keywords.items():
            if kw in query_lower:
                for cid, chunk in chunk_map.items():
                    if chunk.category == target_cat:
                        rrf_scores[cid] = rrf_scores.get(cid, 0.0) * 1.35

        # Sort by final fused score
        sorted_cids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)[:top_k]

        results = []
        for cid in sorted_cids:
            chunk = chunk_map[cid]
            results.append({
                "policy_id": chunk.policy_id,
                "title": chunk.title,
                "category": chunk.category,
                "content": chunk.content,
                "rules": chunk.rules,
                "rrf_score": round(rrf_scores[cid], 4)
            })

        return results

    def retrieve_by_category(self, category: str) -> List[Dict[str, Any]]:
        results = []
        for chunk in self.indexer.chunks:
            if chunk.category.lower() == category.lower() or category.lower() in chunk.category.lower():
                results.append(chunk.to_dict())
        return results
