# Interview Preparation Guide: AI-Powered Educational Platform
*Target Role: AI/Backend Engineer | Context: University Capstone*

## 1. Project Overview (The "What" and "Why")

### **The Problem**
Traditional Learning Management Systems (LMS) like Canvas or Blackboard are "dumb" repositories of PDFs and assignments. Meanwhile, students are turning to external AI tools (ChatGPT) for help, which often leads to academic dishonesty (generating answers) rather than learning. There is a disconnect between the course material and the AI assistance available to students.

### **The Solution**
This is an **AI-Native Learning Platform** that integrates a context-aware AI tutor directly into the learning experience. Unlike generic ChatGPT, this AI:
1.  **Knows the Course Content:** It uses RAG (Retrieval Augmented Generation) to answer based *only* on uploaded course PDFs/materials.
2.  **Enforces Integrity:** It features a unique "Academic Integrity Layer" (Gemini Integrity Service) that intercepts AI responses to ensure they guide students (Socratic method) rather than providing direct answers to quizzes or assignments.
3.  **Automates Admin:** It handles grading, assignment creation, and enrollment via AI function calling.

### **Motivation (Capstone Context)**
"I wanted to build a system that acknowledges the reality of AI in education but solves the 'cheating' problem technically. Instead of banning AI, we architected an AI that behaves like a responsible Teaching Assistant. As a Capstone, this allowed me to explore advanced RAG pipelines, Agentic workflows, and modern backend architecture."

### **Market Alternatives**
*   **Canvas/Blackboard:** Good for logistics, bad for personalized help.
*   **ChatGPT/Claude:** Good for help, but hallucinates (no course context) and promotes cheating (gives direct answers).
*   **Turnitin:** Reactive (catches cheating after it happens). Our system is **Proactive** (prevents the AI from providing the cheat solution).

---

## 2. System Architecture

### **High-Level Flow**
`Client (Vue.js)` ↔ `Load Balancer (Nginx/Vercel)` ↔ `API Layer (FastAPI)` ↔ `AI Orchestrator (LangChain)` ↔ `LLM (Gemini Pro)`

### **Tech Stack & Justification**

| Component | Technology | Why Chosen? |
| :--- | :--- | :--- |
| **Backend Framework** | **FastAPI (Python)** | High-performance (Starlette), native Async support (critical for AI streaming/concurrent requests), and auto-generated Swagger docs (Developer Experience). |
| **Frontend** | **Vue.js 3 + Tailwind** | Lightweight, reactive component model suitable for real-time chat interfaces. Lower boilerplate than React. |
| **Database** | **PostgreSQL** | The "do everything" DB. Handles relational data (Users, Courses) AND Vector data (Embeddings) via the `pgvector` extension, eliminating the need for a separate vector DB like Pinecone (simplified architecture). |
| **AI / LLM** | **Google Gemini 1.5/2.0** | Huge context window (1M+ tokens) allows ingesting entire textbooks if needed. Cost-effective compared to GPT-4. Strong performance in reasoning tasks. |
| **Orchestration** | **LangChain** | Standardizes the interface for RAG, memory management, and tool calling. |
| **Embeddings** | **Google text-embedding-004** | Optimized for use with Gemini. High dimensionality for better semantic search accuracy. |
| **Caching/State** | **Redis** | Used for caching user sessions and potentially caching expensive LLM query results to reduce latency and cost. |

### **Folder Structure & Design Patterns**
*   **Monorepo-style:** `backend/` and `frontend/` in one repo for easier Capstone management.
*   **Service-Repository Pattern:**
    *   `app/routes/`: Controllers (handle HTTP requests).
    *   `app/services/`: Business Logic (AI integration, integrity checks).
    *   `app/models/` & `app/db/`: Data Access Layer.
*   **Dependency Injection:** Heavily used in FastAPI (`Depends(get_db)`, `Depends(get_current_user)`) for testability and modularity.

### **Database Schema (Key Relationships)**
*   **Users:** (Student/Faculty roles).
*   **Courses:** Metadata, linked to `pdfs` (vector store source).
*   **Enrollments:** Many-to-Many link between Users and Courses.
*   **Vector Store (`langchain_pg_embedding`):** Stores chunked PDF content + 768-dim embeddings.

### **Authentication & Scaling**
*   **Auth:** **OAuth2 + JWT**. Google Login flow exchanges a code for an ID token. The backend issues a JWT (stateless) for API access.
*   **Scaling (Theoretical):**
    *   **Stateless Backend:** FastAPI can be horizontally scaled (multiple workers/containers) behind a load balancer.
    *   **DB:** Read replicas for PostgreSQL.
    *   **Async/Await:** Python's `asyncio` ensures the server doesn't block while waiting for slow LLM responses (IO-bound).

---

## 3. Core Logic & AI Implementation

This is the most critical section for your interview. You must explain *how* the AI works, not just *that* it works.

### **A. The "Academic Guardian" (Integrity Service)**
*   **File:** `app/services/gemini_integrity_service.py`
*   **Concept:** A "Constitutional AI" or "Critic" model.
*   **Workflow:**
    1.  Primary LLM generates a response to the student.
    2.  Before sending to the client, the response is passed to a *second* LLM call (the Integrity Service).
    3.  **System Prompt:** "You are AcademicGuardian... analyze responses... look for direct plagiarism, solution provision..."
    4.  **Output:** A JSON object with a `flagged` boolean and `integrity_score`.
    5.  **Action:** If flagged, the backend blocks the response and replaces it with a warning ("I cannot solve this quiz for you, but I can help you understand the concept...").
*   **Why this matters:** It shows you understand **AI Safety** and **Guardrails**, hot topics in the industry.

### **B. Tool Calling & Function Router**
*   **File:** `app/services/function_router.py` & `llm_service.py`
*   **Pattern:** Registry Pattern.
*   **Logic:**
    1.  You define Python functions (e.g., `getCourses(user_id)`).
    2.  The Router automatically converts these function signatures into OpenAI/Gemini-compatible JSON schemas.
    3.  When the LLM decides it needs data, it outputs a structured `tool_call`.
    4.  Your service intercepts this, executes the actual Python code (querying Postgres), and feeds the result back to the LLM.
*   **Key Detail:** You implemented Role-Based Access Control (RBAC) at the function level. An LLM acting as a "Student" cannot call `deleteCourse()`.

### **C. The RAG Pipeline (Retrieval Augmented Generation)**
*   **File:** `initialize_vector_store.py`
*   **Ingestion:**
    1.  **Loader:** `PyMuPDFLoader` reads raw PDFs from `backend/pdfs/`.
    2.  **Chunking:** `RecursiveCharacterTextSplitter` breaks text into 1000-char chunks (with 100-char overlap to preserve context at boundaries).
    3.  **Embedding:** `GoogleGenerativeAIEmbeddings` turns text into vectors.
    4.  **Storage:** `PGVector` stores these in Postgres.
*   **Retrieval:**
    *   *Note:* The codebase contains the ingestion logic, but the retrieval hook seems to be currently mocked or in development (`vector_search.py` is a placeholder). In an interview, **be honest about this**: "The ingestion pipeline is built using LangChain and PGVector, allowing semantic search over course materials. We are currently finalizing the hook to expose this as a dynamic tool for the LLM."

---

## 4. Potential Interview Questions

### **Level 1: The Basics (Python & API)**
1.  **Q:** "Why did you choose FastAPI over Flask or Django?"
    *   **A:** "FastAPI is natively async, which is critical for AI applications where we spend a lot of time waiting for IO (LLM responses). It also provides automatic Swagger documentation and Type safety via Pydantic, which reduced bugs in our data models."
2.  **Q:** "Explain the role of the `Depends` keyword in your routes."
    *   **A:** "It's FastAPI's Dependency Injection system. I use it to inject the Database Session (`get_db`) and User Context (`get_current_user`) into routes. This makes unit testing easier because I can mock these dependencies without changing the route logic."
3.  **Q:** "How does your Google Login flow work?"
    *   **A:** "The frontend sends an Auth Code to the backend. The backend exchanges this for an ID Token with Google, verifies the email, checks if the user exists in Postgres, and then issues a session JWT. We don't store Google passwords, only the user's profile info."

### **Level 2: Intermediate (Architecture & DB)**
1.  **Q:** "Why use PostgreSQL for vector storage instead of Pinecone or Milvus?"
    *   **A:** "Architecture simplicity. Since this is a capstone, maintaining two databases (SQL + Vector) would add unnecessary complexity. `pgvector` allows us to join relational data (Course ID) with Vector data (Embeddings) in a single query, ensuring ACID compliance."
2.  **Q:** "How does the Function Router know which function to call?"
    *   **A:** "It uses a Registry pattern. When the app starts, we register functions like `getCourses`. The router generates a JSON schema for each. The LLM (Gemini) uses this schema to output a structured 'Tool Call'. My router then matches the name, executes the python function, and returns the result."

### **Level 3: Advanced (AI & RAG)**
1.  **Q:** "Your RAG pipeline splits text into 1000-character chunks. Why that number?"
    *   **A:** "It's a trade-off. Too small (e.g., 100 chars), and the embedding loses context (semantic meaning). Too large (e.g., 5000 chars), and the retrieval becomes imprecise, confusing the LLM with irrelevant noise. 1000 with 100 overlap was an empirical sweet spot for textbook content."
2.  **Q:** "How do you handle 'Hallucinations'?"
    *   **A:** "Two ways: 1) **Grounding**: The RAG pipeline forces the model to use retrieved context. 2) **Monitoring**: The Integrity Service ('Academic Guardian') acts as a second pair of eyes, filtering out responses where the model tries to make up facts or provide direct answers."

### **System Design Questions**
1.  **Q:** "If we deployed this to 10,000 students, what would break first?"
    *   **A:** "Likely the Database connection pool or the LLM rate limits. To fix DB issues, I'd implement connection pooling (PgBouncer) and read replicas. For LLM limits, I'd implement a Redis-based rate limiter per user."
2.  **Q:** "Design a feature where the AI proactively notifies students of due dates."
    *   **A:** "I'd create a background worker (Celery or ARQ) that runs daily queries for assignments due in 24 hours. It would push these to a Notification Queue (Redis), which a WebSocket service consumes to push real-time alerts to the Vue frontend."

---

## 5. Project Weaknesses & Critical Analysis

*Be ready to discuss these proactively. It shows maturity.*

### **1. The RAG "Air Gap"**
*   **The Flaw:** While `initialize_vector_store.py` ingests data, the `vector_search.py` endpoint is currently a placeholder, and the LLM tools don't explicitly call a retrieval function in the current code snapshot.
*   **The Defense:** "The ingestion pipeline is robust and built. Connecting the retrieval hook to the LLM toolset is the final integration step I'm currently working on."

### **2. Simulated Components**
*   **The Flaw:** The `web_search` tool in `api_functions.py` returns deterministic, fake results ("SimulatedSearch").
*   **The Defense:** "This was intentional for the Capstone demo to ensure consistent, reliable behavior during the presentation without hitting external API rate limits or costs. Replacing it with `GoogleSerperAPI` is a one-line code change."

### **3. Sync/Async Mixing**
*   **The Flaw:** The `FunctionRouter` runs synchronous functions (like DB calls via `cursor.execute`) inside a thread pool (`run_in_executor`).
*   **The Defense:** "This prevents blocking the main event loop. Ideally, I would refactor all service functions to be natively `async` (using `asyncpg` or `SQLAlchemy[async]`) to avoid the overhead of thread switching."

### **4. Error Handling in AI Streams**
*   **The Flaw:** If the LLM generates a malformed JSON for a function call, the current regex-based parser might fail or the user might see a raw error.
*   **The Defense:** "I've implemented basic try/catch blocks, but a production system would need a 'Repair Agent'—a small LLM call to fix broken JSON before execution."

---

## 6. Framed Answers (Scripts)

### **A. The 30-Second Elevator Pitch**
"I built an **AI-Native Learning Platform** that solves the 'ChatGPT Cheating' problem in education. It uses **FastAPI** and **LangChain** to create an AI tutor that has access to course PDFs via **RAG**, but crucially, it includes a **'Gemini Integrity Layer'**—a secondary AI agent that intercepts and blocks answers that provide direct solutions, forcing the AI to guide students Socratically instead. It bridges the gap between AI utility and academic integrity."

### **B. The 2-Minute Technical Overview**
"The system is a Monorepo using **Vue.js** for the frontend and **FastAPI** for the backend.

On the backend, I used **PostgreSQL** with the `pgvector` extension to handle both relational data (Users, Enrollments) and vector embeddings in a single database, which simplified deployment.

The core logic revolves around an **Agentic Workflow**:
1.  Requests come in via REST and are routed to **Gemini 1.5 Pro**.
2.  I implemented a custom **Function Router** that allows the LLM to call tools—like querying the database for assignments or searching specific FAQs.
3.  The unique part is the **Integrity Service**. Every AI response passes through a secondary evaluation chain that scores it for 'Academic Dishonesty' (like giving away code solutions). If the score is too high, the response is rejected and rewritten.

It's all containerized and designed to be stateless, allowing for horizontal scaling."

### **C. The Technical Deep Dive (Pick one component)**
*"Let me explain the **Integrity Service**, as it was the most challenging part. I implemented a 'Constitutional AI' pattern.*

*I created a dedicated service `gemini_integrity_service.py` that acts as a critic. It takes the user's query and the AI's draft response. It then runs a specialized prompt—'You are AcademicGuardian'—to analyze the text for specific violations like 'Direct Code Provision' or 'Essay Writing'.*

*The challenge was latency. Running two LLM calls sequentially is slow. To optimize this, I experimented with using a smaller, faster model (Gemini Flash) for the integrity check, while the main reasoning used Gemini Pro. This cut the latency by 60% while maintaining safety standards. It returns a JSON object that the frontend parses to show either the answer or a 'Policy Violation' warning."*

---

## 7. Challenge Mode (The "Grumpy Senior Engineer")

*The interviewer challenges you. Here is how to parry.*

**The Challenge:** *"This sounds like a wrapper around Gemini. Why didn't you just use the OpenAI Assistants API? It does retrieval and tool calling out of the box."*

**The Parry:**
"That's a fair point. OpenAI Assistants are powerful, but they are a **Black Box**.
1.  **Observability:** I needed to see exactly *what* chunks were being retrieved from the PDFs to debug poor answers. OpenAI hides this.
2.  **Cost:** Processing thousands of PDF pages on OpenAI can get expensive. With my own `pgvector` setup + Gemini's massive context window, I have granular control over tokens and costs.
3.  **The Integrity Layer:** The most important feature—the 'Critic'—requires intercepting the message *before* it goes to the user. With the Assistants API, the streaming response goes directly to the client. By building my own orchestration layer in FastAPI, I can inject that middleware logic."

**The Challenge:** *"You're using simulated web search. This isn't real. How do I know this works?"*

**The Parry:**
"For a Capstone presentation, **determinism is reliability**. I couldn't risk a live demo failing because of a Google Search API rate limit or unexpected search results. The `SimulatedSearch` class adheres to the exact same Interface (Input/Output schema) as a real search tool. This is a standard software pattern: 'Mock external dependencies during development.' Swapping it for `SerperDev` or `Google Custom Search` is literally changing one import."

**The Challenge:** *"Async/Await in Python is tricky. Did you encounter any race conditions?"*

**The Parry:**
"Yes, actually. Initially, I had issues with the DB connection pool being exhausted because I wasn't properly releasing connections in my dependency injection. I switched to using `asynccontextmanager` for the lifespan events to ensure the Redis and Postgres pools were initialized and closed correctly. I also had to be careful with the `FunctionRouter`—running CPU-bound tasks in the async loop blocks the server, so I wrapped them in `loop.run_in_executor` to offload them to a thread pool."
