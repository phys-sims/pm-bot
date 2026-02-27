from pm_bot.control_plane.retrieval import ChunkUpsert, StubRetriever


def test_stub_retriever_embed_is_deterministic() -> None:
    retriever = StubRetriever()

    assert retriever.embed("hello") == [5.0]
    assert retriever.embed("") == [0.0]


def test_stub_retriever_upsert_and_query_are_safe_noops() -> None:
    retriever = StubRetriever()

    retriever.upsert([ChunkUpsert(chunk_id="c1", text="text", vector=[1.0])])

    assert retriever.query([1.0], filters={"repo_id": 1}, limit=5) == []
