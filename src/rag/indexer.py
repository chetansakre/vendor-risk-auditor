"""
Policy Indexer
Chunks internal security policies and builds dual-retrieval indices:
1. BM25 inverted keyword index
2. Dense semantic embeddings (via sentence-transformers or cosine-similarity vector embeddings)
"""
import os
import re
from typing import List, Dict, Any
import numpy as np
from rank_bm25 import BM25Okapi

class PolicyChunk:
    def __init__(self, policy_id: str, title: str, category: str, content: str, rules: List[str]):
        self.policy_id = policy_id
        self.title = title
        self.category = category
        self.content = content
        self.rules = rules

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "title": self.title,
            "category": self.category,
            "content": self.content,
            "rules": self.rules
        }

class PolicyIndexer:
    def __init__(self, policies_dir: str = None):
        if policies_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            policies_dir = os.path.join(base_dir, "data", "internal_policies")
        self.policies_dir = policies_dir
        self.chunks: List[PolicyChunk] = []
        self.bm25: BM25Okapi = None
        self.embeddings: np.ndarray = None
        self._embedder = None
        self._build_index()

    def _get_embedder(self):
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception as e:
                print(f"[PolicyIndexer] Warning: SentenceTransformer fallback mode: {e}")
                self._embedder = None
        return self._embedder

    def _build_index(self):
        self.chunks = []
        if not os.path.exists(self.policies_dir):
            return

        for fname in os.listdir(self.policies_dir):
            if fname.endswith(".md") or fname.endswith(".txt"):
                fpath = os.path.join(self.policies_dir, fname)
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
                self._parse_policy_file(fname, text)

        if not self.chunks:
            return

        # 1. Build BM25 Index
        corpus = [c.content.lower().split() for c in self.chunks]
        self.bm25 = BM25Okapi(corpus)

        # 2. Build Dense Embeddings
        embedder = self._get_embedder()
        texts = [f"{c.category} - {c.title}: {c.content}" for c in self.chunks]
        if embedder:
            self.embeddings = embedder.encode(texts, normalize_embeddings=True)
        else:
            # Simple TF-IDF term frequency vector fallback
            vocab = sorted(list(set(word for doc in corpus for word in doc)))
            vocab_idx = {w: i for i, w in enumerate(vocab)}
            vectors = np.zeros((len(self.chunks), len(vocab)), dtype=np.float32)
            for doc_idx, doc in enumerate(corpus):
                for w in doc:
                    if w in vocab_idx:
                        vectors[doc_idx, vocab_idx[w]] += 1.0
                norm = np.linalg.norm(vectors[doc_idx])
                if norm > 0:
                    vectors[doc_idx] /= norm
            self.embeddings = vectors

    def _parse_policy_file(self, filename: str, text: str):
        # Split by ## Section
        sections = re.split(r"\n##\s+", text)
        for s in sections:
            s = s.strip()
            if not s or s.startswith("# "):
                continue

            lines = s.split("\n")
            header = lines[0].strip()
            body = "\n".join(lines[1:]).strip()

            # Determine Category
            cat = "General"
            h_lower = header.lower()
            if "encryption" in h_lower or "cryptograph" in h_lower:
                cat = "Encryption"
            elif "ai" in h_lower or "intelligence" in h_lower or "training" in h_lower:
                cat = "AI_Governance"
            elif "retention" in h_lower or "deletion" in h_lower or "expung" in h_lower:
                cat = "Data_Retention"
            elif "subprocessor" in h_lower or "third-party" in h_lower:
                cat = "Subprocessors"
            elif "incident" in h_lower or "breach" in h_lower:
                cat = "Incident_Response"
            elif "access" in h_lower or "auth" in h_lower or "sso" in h_lower or "mfa" in h_lower:
                cat = "Access_Control"
            elif "audit" in h_lower or "soc" in h_lower or "certif" in h_lower:
                cat = "Audits_Certifications"

            rules = [l.strip("- *").strip() for l in lines[1:] if l.strip().startswith(("-", "*"))]

            chunk = PolicyChunk(
                policy_id=f"POL-{cat.upper()[:4]}-{len(self.chunks)+1:02d}",
                title=header,
                category=cat,
                content=s,
                rules=rules
            )
            self.chunks.append(chunk)

    def search_bm25(self, query: str, top_k: int = 3) -> List[tuple]:
        if not self.bm25 or not self.chunks:
            return []
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(self.chunks[i], float(scores[i])) for i in top_indices if scores[i] > 0]

    def search_dense(self, query: str, top_k: int = 3) -> List[tuple]:
        if self.embeddings is None or not self.chunks:
            return []
        embedder = self._get_embedder()
        if embedder:
            q_vec = embedder.encode([query], normalize_embeddings=True)[0]
        else:
            q_vec = np.zeros(self.embeddings.shape[1], dtype=np.float32)
            for w in query.lower().split():
                # fallback matching
                pass
            norm = np.linalg.norm(q_vec)
            if norm > 0:
                q_vec /= norm

        sims = np.dot(self.embeddings, q_vec)
        top_indices = np.argsort(sims)[::-1][:top_k]
        return [(self.chunks[i], float(sims[i])) for i in top_indices]
