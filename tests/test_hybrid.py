import unittest

from langchain_core.documents import Document

from chatbot.hybrid import _tokenize, merge_hybrid_results


class TestHybrid(unittest.TestCase):
    def test_tokenize_lowercase(self):
        self.assertEqual(_tokenize("Art. 46 Cancelamento"), ["art", "46", "cancelamento"])

    def test_merge_prefers_both_lists(self):
        dense = [
            Document(page_content="dense A", metadata={"source": "a.pdf", "page": 1}),
            Document(page_content="dense B", metadata={"source": "b.pdf", "page": 1}),
        ]
        sparse = [
            Document(page_content="sparse C", metadata={"source": "c.pdf", "page": 1}),
            Document(page_content="dense A", metadata={"source": "a.pdf", "page": 1}),
        ]
        merged = merge_hybrid_results(dense, sparse, top_k=3)
        self.assertEqual(len(merged), 3)
        texts = [d.page_content for d in merged]
        self.assertIn("dense A", texts)

    def test_merge_without_sparse_returns_dense(self):
        dense = [Document(page_content="x", metadata={"source": "x.pdf"})]
        self.assertEqual(
            merge_hybrid_results(dense, [], top_k=1)[0].page_content,
            "x",
        )


if __name__ == "__main__":
    unittest.main()
