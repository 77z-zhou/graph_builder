# Knowledge Graph Builder

基于 Neo4j 和 LangChain 的知识图谱构建器（包含 Graph RAG）

## 项目概述

这是一个**知识图谱构建器** - 使用 Python FastAPI 后端系统，通过 LLM（大语言模型）从文档中提取知识图谱，并存储到 Neo4j 图数据库中。系统将文档分块处理，使用 LLM 提取实体和关系，生成嵌入向量，并创建可搜索的图知识库。

**核心工作流程：** 上传文件 → 文档分块 → 使用 LLM 提取实体/关系 → 生成嵌入向量 → 存储到 Neo4j

## 技术栈

- **后端框架：** FastAPI（异步 Python Web 框架）
- **数据库：** Neo4j 图数据库
- **LLM 集成：** LangChain 框架
  - 支持的 LLM：DeepSeek (`deepseek-chat`)、阿里通义千问 (`qwen3-max` via DashScope)
- **嵌入模型：** Qwen/Qwen3-Embedding-0.6B（sentence transformers）、HuggingFace embeddings
- **文档处理：** PyMuPDF（PDF）、Unstructured（多格式加载器）
- **API 设计：** RESTful with async/await、Pydantic 验证

## 架构

代码库遵循**分层架构**模式：

```
backend/
├── app.py                  # FastAPI 应用设置、中间件配置
├── router.py               # API 路由定义
├── service.py              # 核心业务逻辑（编排层）
├── config.py               # Pydantic 环境配置设置
├── app_entities.py         # Pydantic 模型和 API schemas
├── utils.py                # 工具函数
├── middleware.py           # 自定义中间件（GZip 压缩）
├── chunks/                 # 上传期间的临时分块存储
├── merged_files/           # 合并后的上传文件
└── src/                    # 核心业务逻辑模块
    ├── common/
    │   ├── cyphers.py      # Neo4j Cypher 查询模板
    │   └── prompts.py      # LLM 实体提取提示词
    ├── document_processors/
    │   ├── doc_chunk.py    # 文档分块逻辑
    │   └── local_file.py   # 本地文件加载
    ├── graph_llm/
    │   └── graph_transform.py  # 基于 LLM 的图提取
    ├── graph_db_access.py  # Neo4j 数据库操作（DAO 层）
    ├── llm.py              # LLM 初始化和 token 跟踪
    └── embedding.py        # 嵌入模型管理
```

### 关键层次

1. **API 层** (`router.py`, `app.py`) - FastAPI 端点、请求验证
2. **服务层** (`service.py`) - 业务逻辑编排、文件上传处理
3. **数据访问层** (`src/graph_db_access.py`) - Neo4j CRUD 操作及重试逻辑
4. **文档处理** (`src/document_processors/`) - 文件加载和分块
5. **LLM 集成** (`src/graph_llm/`, `src/llm.py`) - 实体提取和 token 跟踪
6. **嵌入层** (`src/embedding.py`) - 向量生成

### 图数据库模式

**节点类型：**
- `Document` - 源文档及元数据（fileName、status、nodeCount 等）
- `Chunk` - 带嵌入向量的文本块，链接到文档
- `__Entity__` / `__ENTITY__` - 提取的实体（Person、Organization 等）

**关系类型：**
- `PART_OF` - 文本块属于文档
- `FIRST_CHUNK` - 文档的第一个文本块
- `NEXT_CHUNK` - 文本块顺序
- `HAS_ENTITY` - 文本块包含提取的实体
- 实体间关系（根据提取结果变化）

## 环境配置

应用使用 Pydantic `BaseSettings` 通过 `.env` 文件进行配置。必需的环境变量：

```bash
# Neo4j 数据库
NEO4J_URI="bolt://127.0.0.1:7687"
NEO4J_USERNAME="neo4j"
NEO4J_PASSWORD="your_password"
NEO4J_DATABASE="neo4j"

# LLM 模型（格式：model_name,api_key,base_url）
LLM_MODEL_deepseek_deepseek_chat="deepseek-chat,sk-xxx,https://api.deepseek.com/v1"
LLM_MODEL_dashscope_qwen3_max="qwen3-max,sk-xxx,https://dashscope.aliyuncs.com/compatible-mode/v1"

# 嵌入模型
EMBEDDING_MODEL="sentence_transformer"

# 图构建参数
UPDATE_GRPAH_CHUNK_BATCH_SIZE=20
MAX_TOKEN_CHUNK_SIZE=10000

# Agent 设置
ENABLE_USER_AGENT=true
```

## 运行应用

**启动服务器：**
```bash
cd backend
python app.py
```

应用默认运行在 `http://0.0.0.0:7860`。

**健康检查：** `GET /health`

**主要 API 端点：**
- `POST /upload` - 分块文件上传
- `POST /extract` - 知识图谱提取（核心端点）
- `POST /backend_connection_configuration` - Neo4j 连接测试

## 核心处理模式

系统支持三种处理模式（在 `config.py` 中定义）：

1. **START_FROM_BEGINNING** - 从头开始处理整个文档
2. **DELETE_ENTITIES_AND_START_FROM_BEGINNING** - 删除现有实体并重新提取
3. **START_FROM_LAST_PROCESSED_POSITION** - 从上次处理位置继续

## 关键实现细节

### 文件上传流程
文件以分块方式上传（`backend/chunks/`），合并（`backend/merged_files/`），然后处理。分块机制处理大文件和可恢复上传。

### LLM 集成
- LLM 模型在 `src/llm.py` 中使用 LangChain 的 `init_chat_model()` 初始化
- Token 使用通过 `UniversalTokenUsageHandler` 回调跟踪
- 支持 DeepSeek 和 Qwen 模型，可配置 API 密钥

### 数据库操作
- 所有 Neo4j 操作通过 `src/graph_db_access.py` 中的 `GraphDBDataAccess` 类进行
- 包含死锁处理的自动重试逻辑（`execute_query` 方法）
- 使用 Neo4j 向量索引进行嵌入向量的相似性搜索

### 文档处理流程
1. 文件上传并合并
2. 在 Neo4j 中创建文档节点
3. 文档分割成文本块（`CreateChunksofDocument`）
4. 对每个文本块：
   - 生成嵌入向量
   - 使用 LLM 提取实体/关系（`LLMGraphTransformer`）
   - 将文本块和嵌入向量存储到 Neo4j
   - 将实体链接到文本块
5. 更新文档节点的计数和状态

## 代码模式

- 整个代码库一致使用**类型提示**
- 使用 **Pydantic 模型**进行数据验证（`app_entities.py`）
- API 路由中的 I/O 操作使用 **Async/await**
- 配置了统一的**日志记录**格式
- 通过 try-except 块和文档节点中的状态跟踪进行**错误处理**
- 通过 FastAPI 的 `Depends()` 进行**依赖注入**

## 重要说明

- 代码库使用**中英文混合注释** - 这是故意的
- 目前**没有自动化测试** - 通过 `test.ipynb` Jupyter notebook 手动测试
- 文档状态在 Neo4j 中跟踪："New"、"Processing"、"Completed"、"Failed"、"Cancelled"
- Token 使用被跟踪，可以从 `UniversalTokenUsageHandler` 检索
- 系统支持处理来自多个来源的文件：本地文件、网址、Bilibili 视频、Wikipedia

## 许可证

请参考项目许可证文件。
