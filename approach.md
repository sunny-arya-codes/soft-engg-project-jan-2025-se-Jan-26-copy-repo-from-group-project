# AI & RAG Implementation Approach

## Overview

The application leverages a sophisticated AI architecture built on **Google's Gemini 1.5 Pro/Flash** models, orchestrated via **LangChain**. The system is designed to provide intelligent, context-aware responses by combining a powerful LLM with a flexible function-calling mechanism and a Retrieval-Augmented Generation (RAG) pipeline for document knowledge.

### Core Components

1.  **LLM Service (`backend/app/services/llm_service.py`)**:
    *   **Model Selection**: Dynamically selects between models (e.g., `gemini-1.5-pro`, `gemini-2.0-flash`) based on availability and task requirements (e.g., fallback logic).
    *   **Tool Integration**: Utilizes Gemini's native function calling capabilities. The LLM is provided with a suite of tools (defined in `api_functions.py`) to fetch real-time data like user profiles, courses, and assignments.
    *   **System Prompting**: Uses a robust system prompt that instructs the AI to act as an educational assistant, guiding it on when and how to use tools versus answering directly.

2.  **Function Routing (`backend/app/services/function_router.py`)**:
    *   Acts as a middleware between the LLM and the backend logic.
    *   Registers functions with detailed JSON schemas (OpenAI-compatible format) so the LLM understands the purpose and parameters of each tool.
    *   Handles the execution of functions and returns structured results back to the LLM for final response generation.

3.  **RAG Ingestion Pipeline (`backend/initialize_vector_store.py`)**:
    *   **Document Loading**: Loads educational resources (PDFs) from the `pdfs/` directory using `PyMuPDFLoader`.
    *   **Vector Database**: Utilizes **PostgreSQL with `pgvector`** as the vector store, allowing seamless integration with the existing application database.
    *   **Embeddings**: Generates vector embeddings using **Google's `models/text-embedding-004`**, ensuring high-quality semantic representation of the content.

---

## RAG Pipeline: Strategy & Trade-offs

### Question:
*When you built the RAG pipeline for that project, how did you handle the "Context Window vs. Cost" trade-off? Specifically, what chunking strategy did you use for the documents, and how did you ensure the retrieved chunks were actually relevant enough to answer the query without burning through unnecessary tokens?*

### Answer:

#### 1. Context Window vs. Cost Trade-off
While modern models like Gemini 1.5 Pro boast massive context windows (up to 1M+ tokens), blindly feeding entire documents into the context is inefficient and costly. We approached this trade-off by implementing a **Retrieval-Augmented Generation (RAG)** architecture rather than a full-context approach.

*   **Cost Efficiency**: By indexing documents and retrieving only the most relevant snippets, we significantly reduce the input token count per request. This keeps operational costs low, as we only pay for the tokens actually needed to answer the query, rather than processing megabytes of PDF text for every interaction.
*   **Latency**: Smaller prompts result in faster generation times, providing a snappier user experience compared to the latency incurred by processing massive contexts.

#### 2. Chunking Strategy
We implemented a balanced chunking strategy in `initialize_vector_store.py` using LangChain's `RecursiveCharacterTextSplitter`:

*   **Chunk Size**: **1000 characters**.
    *   *Rationale*: This size is large enough to capture complete thoughts and self-contained concepts (roughly a paragraph or two), providing the LLM with sufficient context to understand the snippet in isolation.
*   **Chunk Overlap**: **100 characters**.
    *   *Rationale*: This overlap ensures continuity between chunks. It prevents critical information (like a sentence connecting two ideas) from being split across boundaries, which could otherwise result in semantic loss.

#### 3. Ensuring Relevance
To ensure retrieved chunks are relevant and "token-worthy," we relied on high-quality semantic search rather than simple keyword matching:

*   **Semantic Embeddings**: We utilized **Google's `models/text-embedding-004`**. This model is highly effective at capturing the *meaning* of text, not just the wording. This allows the system to retrieve chunks that conceptually answer a user's question, even if the user uses different terminology than the source document.
*   **Vector Similarity**: By using **Cosine Similarity** via `pgvector`, we rank chunks based on their semantic proximity to the query. This ensures that the top-k retrieved chunks (typically the top 3-5) are the most likely to contain the answer, minimizing the noise passed to the LLM.

This combination of moderate chunk sizes and state-of-the-art semantic embeddings allows us to maximize the information density of the prompt, ensuring high-quality answers without "burning through unnecessary tokens."
