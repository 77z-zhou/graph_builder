# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Knowledge Graph Builder** - a Python FastAPI backend system that extracts knowledge graphs from documents using LLMs (Large Language Models) and stores them in Neo4j graph database. The system processes documents in chunks, extracts entities and relationships using LLMs, generates embeddings, and creates a searchable graph knowledge base.

**Core workflow:** Upload file → Chunk document → Extract entities/relationships with LLM → Generate embeddings → Store in Neo4j

## Technology Stack

- **Backend Framework:** FastAPI (async Python web framework)
- **Database:** Neo4j graph database
- **LLM Integration:** LangChain framework
  - Supported LLMs: DeepSeek (`deepseek-chat`), Alibaba Qwen (`qwen3-max` via DashScope)
- **Embeddings:** Qwen/Qwen3-Embedding-0.6B (sentence transformers), HuggingFace embeddings
- **Document Processing:** PyMuPDF (PDF), Unstructured (multi-format loader)
- **API Design:** RESTful with async/await, Pydantic validation

## Architecture

The codebase follows a **layered architecture** pattern:

```
backend/
├── app.py                  # FastAPI application setup, middleware configuration
├── router.py               # API route definitions
├── service.py              # Core business logic (orchestration layer)
├── config.py               # Pydantic settings for environment configuration
├── app_entities.py         # Pydantic models & API schemas
├── utils.py                # Utility functions
├── middleware.py           # Custom middleware (GZip compression)
├── chunks/                 # Temporary chunk storage during upload
├── merged_files/           # Merged uploaded files
└── src/                    # Core business logic modules
    ├── common/
    │   ├── cyphers.py      # Neo4j Cypher query templates
    │   └── prompts.py      # LLM prompts for entity extraction
    ├── document_processors/
    │   ├── doc_chunk.py    # Document chunking logic
    │   └── local_file.py   # Local file loading
    ├── graph_llm/
    │   └── graph_transform.py  # LLM-based graph extraction
    ├── graph_db_access.py  # Neo4j database operations (DAO layer)
    ├── llm.py              # LLM initialization & token tracking
    └── embedding.py        # Embedding model management
```

### Key Layers

1. **API Layer** (`router.py`, `app.py`) - FastAPI endpoints, request validation
2. **Service Layer** (`service.py`) - Business logic orchestration, file upload handling
3. **Data Access Layer** (`src/graph_db_access.py`) - Neo4j CRUD operations with retry logic
4. **Document Processing** (`src/document_processors/`) - File loading and chunking
5. **LLM Integration** (`src/graph_llm/`, `src/llm.py`) - Entity extraction and token tracking
6. **Embedding Layer** (`src/embedding.py`) - Vector generation

### Graph Schema

**Node Types:**
- `Document` - Source documents with metadata (fileName, status, nodeCount, etc.)
- `Chunk` - Text chunks with embeddings, linked to Documents
- `__Entity__` / `__ENTITY__` - Extracted entities (Person, Organization, etc.)

**Relationship Types:**
- `PART_OF` - Chunk belongs to Document
- `FIRST_CHUNK` - First chunk of document
- `NEXT_CHUNK` - Sequential chunk ordering
- `HAS_ENTITY` - Chunk contains extracted entities
- Entity-to-entity relationships (varies by extraction)

## Environment Configuration

The application uses Pydantic `BaseSettings` for configuration via `.env` file. Required environment variables:

```bash
# Neo4j Database
NEO4J_URI="bolt://127.0.0.1:7687"
NEO4J_USERNAME="neo4j"
NEO4J_PASSWORD="your_password"
NEO4J_DATABASE="neo4j"

# LLM Models (format: model_name,api_key,base_url)
LLM_MODEL_deepseek_deepseek_chat="deepseek-chat,sk-xxx,https://api.deepseek.com/v1"
LLM_MODEL_dashscope_qwen3_max="qwen3-max,sk-xxx,https://dashscope.aliyuncs.com/compatible-mode/v1"

# Embedding Model
EMBEDDING_MODEL="sentence_transformer"

# Graph Construction Parameters
UPDATE_GRPAH_CHUNK_BATCH_SIZE=20
MAX_TOKEN_CHUNK_SIZE=10000

# Agent Settings
ENABLE_USER_AGENT=true
```

## Running the Application

**Start the server:**
```bash
cd backend
python app.py
```

The application runs on `http://0.0.0.0:7860` by default.

**Health check:** `GET /health`

**Main API endpoints:**
- `POST /upload` - Chunked file upload
- `POST /extract` - Knowledge graph extraction (core endpoint)
- `POST /backend_connection_configuration` - Neo4j connection test

## Core Processing Modes

The system supports three processing modes (defined in `config.py`):

1. **START_FROM_BEGINNING** - Process entire document from scratch
2. **DELETE_ENTITIES_AND_START_FROM_BEGINNING** - Delete existing entities and re-extract
3. **START_FROM_LAST_PROCESSED_POSITION** - Resume from last processed chunk

## Key Implementation Details

### File Upload Process
Files are uploaded in chunks (`backend/chunks/`), merged (`backend/merged_files/`), then processed. The chunking mechanism handles large files and resumable uploads.

### LLM Integration
- LLM models are initialized in `src/llm.py` using LangChain's `init_chat_model()`
- Token usage is tracked via `UniversalTokenUsageHandler` callback
- Supports DeepSeek and Qwen models with configurable API keys

### Database Operations
- All Neo4j operations go through `GraphDBDataAccess` class in `src/graph_db_access.py`
- Includes automatic retry logic for deadlock handling (`execute_query` method)
- Uses Neo4j vector index for similarity search on embeddings

### Document Processing Flow
1. File uploaded and merged
2. Document node created in Neo4j
3. Document split into chunks (`CreateChunksofDocument`)
4. For each chunk:
   - Generate embedding
   - Extract entities/relationships using LLM (`LLMGraphTransformer`)
   - Store chunk with embedding in Neo4j
   - Link entities to chunks
5. Update document node with counts and status

## Code Patterns

- **Type hints** are used consistently throughout the codebase
- **Pydantic models** for data validation (`app_entities.py`)
- **Async/await** for I/O operations in API routes
- **Logging** is configured with consistent formatting
- **Error handling** with try-except blocks and status tracking in Document nodes
- **Dependency injection** via FastAPI's `Depends()` for credentials

## Development Commands

**Install dependencies:**
```bash
cd backend
pip install -r requirements.txt
```

**Start backend server:**
```bash
cd backend
python app.py
# Server runs on http://0.0.0.0:7860
```

**Start frontend test server (optional):**
```bash
cd frontend
python -m http.server 8000
# Then open http://localhost:8000/test.html in browser
```

**Check Neo4j connection:**
- Use `POST /backend_connection_configuration` endpoint
- Or use the frontend test interface at `test.html`

## Graph RAG Agent

The system includes a Graph RAG agent for natural language querying:
- Located in `backend/src/rag/simple_graph_rag/`
- Uses LangGraph with `InMemorySaver` for state management
- Implements `GenerateCypherTool` for Cypher query generation
- Accessible via `POST /chat` endpoint with `mode=simple`
- Supports streaming responses via Server-Sent Events (SSE)

## Frontend Architecture

The frontend is a **static HTML testing platform** (no build process required):
- **test.html** - Main API testing interface for all endpoints
- **graph-chat.html** - Dedicated Graph RAG chat interface
- Pure HTML/CSS/JavaScript - can be opened directly in browser
- For production testing, use simple HTTP server: `python -m http.server 8000`

## Key Data Flows

**File Upload → Extraction Flow:**
1. `POST /upload` - Chunked file upload (5MB chunks)
2. Files stored in `backend/chunks/`, then merged to `backend/merged_files/`
3. `POST /extract` with `source_type="local_file"` - Triggers extraction
4. Processing handled by `processing_source()` in `service.py`
5. Status updates written to Document node in Neo4j

**Graph RAG Chat Flow:**
1. `POST /chat` with `mode=simple`
2. `SimpleGraphRagAgent` creates LangGraph agent with `GenerateCypherTool`
3. Agent generates Cypher queries using LLM
4. Queries executed on Neo4j, results streamed back via SSE

## Important Notes

- The codebase uses **mixed Chinese/English comments** - this is intentional
- **No automated tests** currently exist - testing is done manually via `test.ipynb` Jupyter notebook or frontend HTML pages
- Document status is tracked in Neo4j: "New", "Processing", "Completed", "Failed", "Cancelled"
- Token usage is tracked and can be retrieved from the `UniversalTokenUsageHandler`
- The system supports processing files from multiple sources: local files, web URLs, Bilibili videos, Wikipedia
- Chunked upload uses 5MB chunks to handle large files and avoid timeouts
- Vector index named "vector" must exist in Neo4j for embedding similarity search
- GDS (Graph Data Science) library is optional - system checks for its availability
