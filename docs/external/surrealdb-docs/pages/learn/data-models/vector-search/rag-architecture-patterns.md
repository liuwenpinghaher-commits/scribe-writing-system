---
title: "https://surrealdb.com/docs/learn/data-models/vector-search/rag-architecture-patterns"
url: "https://surrealdb.com/docs/learn/data-models/vector-search/rag-architecture-patterns"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/data-models/vector-search/rag-architecture-patterns

Source: https://surrealdb.com/docs/learn/data-models/vector-search/rag-architecture-patterns

Retrieval-augmented generation (RAG) combines retrieval from your own data with generation from a language model. Instead of relying only on the model’s training data, you ground answers in chunks of text (and sometimes structured facts) that you control. SurrealDB is then used for storage and retrieval, allowing you to keep chunk text, metadata, access rules, and vector embeddings in one database and query them with SurrealQL.
##  What RAG changes[](https://surrealdb.com/docs/learn/data-models/vector-search/rag-architecture-patterns#what-rag-changes)
A plain LLM call answers from parametric memory only. RAG adds a knowledge plane to this, in which documents are split into chunks, each chunk gets an embedding from a model you choose, and at query time you retrieve the most relevant chunks before (or while) the LLM writes an answer.
##  Typical pipeline stages[](https://surrealdb.com/docs/learn/data-models/vector-search/rag-architecture-patterns#typical-pipeline-stages)
  1. 1.
Ingest: Load sources (files, web pages, tickets, database exports).
  2. 2.
Chunk: Split text into segments with stable boundaries (headings, paragraphs, token limits) and optional overlap so ideas are not split awkwardly.
  3. 3.
Embed: Call an embedding API or local model; store the resulting vector with each chunk. See [Embedding pipelines](https://surrealdb.com/docs/learn/data-models/vector-search/embedding-pipelines) and the [embeddings integrations](https://surrealdb.com/docs/build/integrations/embeddings-providers/fastembed) for options outside the database.
  4. 4.
Index: Define [vector indexes](https://surrealdb.com/docs/learn/data-models/vector-search/vector-indexes) (for example HNSW) on embedding fields, and optionally [full-text indexes](https://surrealdb.com/docs/learn/data-models/full-text-search/overview) on chunk text for lexical search.
  5. 5.
Retrieve: For a user question, embed the query (or use the same model family as the corpus), run similarity search, optionally fuse with keyword results (see [Hybrid search](https://surrealdb.com/docs/learn/data-models/vector-search/hybrid-search)).
  6. 6.
Generate: Pass the top chunks as context to the LLM, with instructions to cite or stay within that context.

##  Retrieval patterns[](https://surrealdb.com/docs/learn/data-models/vector-search/rag-architecture-patterns#retrieval-patterns)
  * •
Dense retrieval: KNN over embeddings with [`vector::distance::knn()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/vector#vectordistanceknn) and the patterns in [Similarity search](https://surrealdb.com/docs/learn/data-models/vector-search/similarity-search). Good for paraphrases and conceptual match.
  * •
Hybrid retrieval: Combine dense scores with [full-text search](https://surrealdb.com/docs/learn/data-models/full-text-search/overview) when exact product names, error codes, or legislation matter; use [`search::rrf()`](https://surrealdb.com/docs/learn/data-models/vector-search/hybrid-search) or related helpers as described under [Hybrid search](https://surrealdb.com/docs/learn/data-models/vector-search/hybrid-search).

Re-ranking (a second model that scores the top _k_ candidates) is often implemented in the application layer; SurrealDB supplies the candidate set efficiently.
##  Chunking, metadata, and citations[](https://surrealdb.com/docs/learn/data-models/vector-search/rag-architecture-patterns#chunking-metadata-and-citations)
There is no single best chunk size: smaller chunks improve precision but lose surrounding context; larger chunks add context but dilute embeddings. Many teams store title, heading path, or summary fields to improve retrieval without inflating the embedded body.
For citations, persist enough metadata to map a chunk back to a human-readable source (page, anchor, ticket id). The LLM should only “see” what you retrieved; clear provenance reduces hallucinated references.
##  Operations and quality[](https://surrealdb.com/docs/learn/data-models/vector-search/rag-architecture-patterns#operations-and-quality)
  * •
Embedding model changes usually require re-embedding the corpus or maintaining a version dimension; plan migrations before switching dimensions or distance metrics.
  * •
Staleness: when sources update, replace or invalidate affected chunks so answers do not quote obsolete text.
  * •
Evaluation: track retrieval hit rate, user thumbs-up/down, or offline benchmarks on labelled questions.

##  Resources[](https://surrealdb.com/docs/learn/data-models/vector-search/rag-architecture-patterns#resources)
  * •
[Vector search cheat sheet](https://surrealdb.com/docs/learn/data-models/vector-search/vector-indexes#vector-search-cheat-sheet)
  * •
[Vector search overview](https://surrealdb.com/docs/learn/data-models/vector-search/overview)
  * •
[Hybrid search](https://surrealdb.com/docs/learn/data-models/vector-search/hybrid-search)
  * •
[Full-text search overview](https://surrealdb.com/docs/learn/data-models/full-text-search/overview)
  * •
[Embedding pipelines](https://surrealdb.com/docs/learn/data-models/vector-search/embedding-pipelines)
  * •
[Vector functions](https://surrealdb.com/docs/reference/query-language/functions/database-functions/vector#vector-functions)
  * •
[Vector search indexes](https://surrealdb.com/docs/reference/query-language/statements/define/indexes#vector-search-indexes)
  * •
[FastEmbed and embeddings integrations](https://surrealdb.com/docs/build/integrations/embeddings-providers/fastembed)
  * •
[YouTube: Vector search intro](https://www.youtube.com/watch?v=MqddPmgKSCs)
