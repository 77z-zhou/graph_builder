# Knowledge Graph Builder

> 基于 Neo4j 和 LangChain 的智能知识图谱构建与检索系统（支持 Graph RAG）

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green)](https://fastapi.tiangolo.com/)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.x%2B-orange)](https://neo4j.com/)
[![LangChain](https://img.shields.io/badge/LangChain-Latest-yellow)](https://langchain.com/)

## 📖 项目简介

这是一个功能完整的**知识图谱构建器**，使用大语言模型（LLM）从各种文档源中自动提取实体和关系，构建结构化的知识图谱，并提供基于图谱的智能检索和对话功能。

### 核心功能

- 📄 **多源文档处理**：支持本地文件（PDF/TXT/DOCX）、网页 URL、Bilibili 视频、维基百科
- 🧠 **智能实体提取**：基于 LLM 自动识别文档中的实体和关系
- 🔍 **向量检索**：使用嵌入向量进行语义搜索
- 💬 **Graph RAG 对话**：支持两种模式的图谱问答
  - **Generate Cypher**：自动生成 Cypher 查询语句
  - **Graph Retrieve**：基于向量相似度 + fulltext的图谱检索
- 📊 **可视化分析**：支持 Neo4j Browser 直接查看图谱

### 工作流程

```
上传文档 → 文档分块 → LLM提取实体关系 → 生成嵌入向量 → 存储到Neo4j → 智能检索对话
```

---

## 🛠 技术栈

### 后端
- **框架**：FastAPI（异步 Python Web 框架）
- **数据库**：Neo4j 图数据库
- **LLM 集成**：LangChain
  - DeepSeek (`deepseek-chat`)
  - 阿里通义千问 (`qwen3-max`)
- **嵌入模型**：Sentence Transformers (Qwen3-Embedding-0.6B)
- **文档处理**：PyMuPDF、Unstructured

### 前端
- **框架**：Vue 3 + Vite
- **UI 库**：Element Plus
- **状态管理**：Pinia
- **路由**：Vue Router
- **功能**：
  - 文件上传与进度显示
  - 知识图谱提取配置
  - Neo4j 连接管理
  - Graph RAG 对话（两种模式）
  - 暗色/亮色主题切换

---

## 📦 安装部署

### 前置要求

- Python 3.9+
- Neo4j 5.x+
- pip

### 1. 克隆项目

```bash
git clone <repository-url>
cd graph_builder
```

### 2. 安装依赖

**后端依赖：**
```bash
cd backend
pip install -r requirements.txt
```

**前端依赖：**
```bash
cd frontend
npm install
```

### 3. 配置环境变量

在 `backend/` 目录下创建 `.env` 文件：

```bash
# Neo4j 数据库连接
NEO4J_URI="bolt://127.0.0.1:7687"
NEO4J_USERNAME="neo4j"
NEO4J_PASSWORD="your_password"
NEO4J_DATABASE="neo4j"

# LLM 模型配置（格式：model_name,api_key,base_url）
# DeepSeek
LLM_MODEL_deepseek_deepseek_chat="deepseek-chat,sk-your-deepseek-key,https://api.deepseek.com/v1"
# 通义千问
LLM_MODEL_dashscope_qwen3_max="qwen3-max,sk-your-qwen-key,https://dashscope.aliyuncs.com/compatible-mode/v1"

# 嵌入模型
EMBEDDING_MODEL="sentence_transformer"

# 图构建参数
UPDATE_GRPAH_CHUNK_BATCH_SIZE=20
MAX_TOKEN_CHUNK_SIZE=10000

# Agent 设置
ENABLE_USER_AGENT=true
```

### 4. 启动 Neo4j

确保 Neo4j 服务正在运行：

```bash
# 使用 Docker 运行 Neo4j
docker run -d \
    --name neo4j \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/your_password \
    neo4j:latest
```

### 5. 启动后端服务

```bash
cd backend
python app.py
```

服务将在 `http://localhost:7860` 启动。

### 6. 启动前端

**开发模式（热重载）：**
```bash
cd frontend
npm run dev
```

前端将在 `http://localhost:5173` 启动。

**生产构建：**
```bash
cd frontend
npm run build
```

构建产物将输出到 `frontend/dist/` 目录，可部署到任何静态文件服务器。

---

## 🚀 使用指南

### 通过 Vue 前端界面

1. **访问前端**：打开浏览器访问 `http://localhost:5173`

2. **连接 Neo4j**：
   - 点击左上角的"连接Neo4j"按钮
   - 系统会自动使用配置文件中的连接信息
   - 连接成功后按钮会显示绿色"已连接"

3. **选择模型**：
   - 在右上角选择用于图谱构建和对话的 LLM 模型
   - 支持：DeepSeek Chat、Qwen 3 Max

4. **上传文档**：
   - 在"文件上传"区域拖拽或点击选择文件
   - 支持格式：PDF、TXT、DOCX（最大 100MB）
   - 点击"上传文件"按钮
   - 查看上传进度和状态

5. **提取知识图谱**：
   - 选择数据源：
     - **本地文件**：使用已上传的文件
     - **网页 URL**：输入网页链接
     - **Bilibili**：输入视频链接
     - **维基百科**：输入搜索关键词
   - 配置参数：
     - Token 块大小（默认 10000）
     - 块重叠大小（默认 200）
   - 点击"提取知识图谱"按钮
   - 在文档列表中查看处理进度

6. **Graph RAG 对话**：
   - 在右侧聊天面板选择 Agent 模式：
     - **Cypher Generate**：AI 自动生成 Cypher 查询语句
     - **Graph Retriever**：基于向量+全文检索的混合搜索
   - Graph Retriever 模式下可选择特定文档进行对话
   - 输入问题并开始对话

7. **切换主题**：
   - 点击右上角的太阳/月亮图标切换暗色/亮色主题

### 方式二：通过 API

#### 健康检查

```bash
curl http://localhost:7860/health
```

#### 测试数据库连接

```bash
curl -X POST http://localhost:7860/backend_connection_configuration \
  -F "uri=bolt://127.0.0.1:7687" \
  -F "userName=neo4j" \
  -F "password=your_password" \
  -F "database=neo4j"
```

#### 上传文件

```bash
curl -X POST http://localhost:7860/upload \
  -F "file=@/path/to/document.pdf" \
  -F "chunkNumber=1" \
  -F "totalChunks=1" \
  -F "originalname=document.pdf" \
  -F "model=deepseek-deepseek-chat" \
  -F "uri=bolt://127.0.0.1:7687" \
  -F "userName=neo4j" \
  -F "password=your_password" \
  -F "database=neo4j"
```

#### 提取知识图谱

```bash
curl -X POST http://localhost:7860/extract \
  -F "uri=bolt://127.0.0.1:7687" \
  -F "userName=neo4j" \
  -F "password=your_password" \
  -F "database=neo4j" \
  -F "source_type=local_file" \
  -F "file_name=document.pdf" \
  -F "model=deepseek-deepseek-chat" \
  -F "token_chunk_size=10000"
```

#### Graph RAG 聊天

```bash
curl -X POST http://localhost:7860/chat \
  -F "uri=bolt://127.0.0.1:7687" \
  -F "userName=neo4j" \
  -F "password=your_password" \
  -F "database=neo4j" \
  -F "question=这个文档主要讲了什么？" \
  -F "mode=graph_retrieve" \
  -F "model=deepseek-deepseek-chat"
```

---

## 📂 项目结构

```
graph_builder/
├── backend/
│   ├── app.py                    # FastAPI 应用入口
│   ├── router.py                 # API 路由定义
│   ├── service.py                # 核心业务逻辑
│   ├── config.py                 # 配置管理
│   ├── app_entities.py           # Pydantic 数据模型
│   ├── middleware.py             # 中间件
│   ├── utils.py                  # 工具函数
│   ├── chunks/                   # 临时上传分块
│   ├── merged_files/             # 合并后的文件
│   └── src/                      # 核心业务模块
│       ├── common/
│       │   ├── cyphers.py        # Cypher 查询模板
│       │   └── prompts.py        # LLM 提示词
│       ├── document_processors/
│       │   ├── doc_chunk.py      # 文档分块
│       │   └── local_file.py     # 文件加载
│       ├── graph_llm/
│       │   └── graph_transform.py # LLM 图谱提取
│       ├── graph_db_access.py    # Neo4j 数据访问层
│       ├── llm.py                # LLM 初始化
│       ├── embedding.py          # 嵌入模型
│       └── rag/                  # Graph RAG 模块
│           ├── agent.py          # RAG Agent
│           ├── state.py          # Agent 状态管理
│           └── tools/            # RAG 工具
│               ├── generate_cypher.py
│               └── graph_retrieve.py
├── frontend/                     # Vue 3 前端应用
│   ├── src/
│   │   ├── components/           # Vue 组件
│   │   │   └── ChatPanel.vue     # 聊天面板组件
│   │   ├── views/                # 页面视图
│   │   │   ├── Layout.vue        # 主布局
│   │   │   └── Dashboard.vue     # 仪表板页面
│   │   ├── stores/               # Pinia 状态管理
│   │   │   ├── documents.js      # 文档状态
│   │   │   └── neo4j.js          # Neo4j 配置状态
│   │   ├── api/                  # API 封装
│   │   │   └── graph.js          # 图谱相关 API
│   │   ├── router/               # Vue Router 配置
│   │   ├── App.vue               # 根组件
│   │   ├── main.js               # 应用入口
│   │   ├── style.css             # 全局样式
│   │   └── dark-theme.css        # 暗色主题样式
│   ├── public/                   # 静态资源
│   ├── index.html                # HTML 模板
│   ├── package.json              # npm 依赖配置
│   ├── vite.config.js            # Vite 配置
│   └── README.md                 # 前端说明
├── requirements.txt              # Python 依赖
├── CLAUDE.md                     # 项目开发指南
└── README.md                     # 本文件
```

---

## 🗄 数据库模式

### 节点类型

- **Document**：源文档节点
  - 属性：`fileName`、`status`、`nodeCount`、`relationshipCount`、`url` 等

- **Chunk**：文档分块节点
  - 属性：`text`、`embedding`（向量）、`index` 等

- **__Entity__**：提取的实体节点
  - 属性：`id`、`description`、`type`、`embedding` 等

### 关系类型

- `PART_OF`：文本块属于文档
- `FIRST_CHUNK`：文档的首个文本块
- `NEXT_CHUNK`：文本块之间的顺序
- `HAS_ENTITY`：文本块包含实体
- `[:HAS_ENTITY]->(e)`：实体间的语义关系

---

## ⚙️ 高级配置

### 处理模式

支持三种文档处理模式：

1. **START_FROM_BEGINNING**：从头开始处理
2. **DELETE_ENTITIES_AND_START_FROM_BEGINNING**：删除现有实体并重新提取
3. **START_FROM_LAST_PROCESSED_POSITION**：从中断位置继续

### 后处理任务

可通过 API 执行的后处理任务：

- **materialize_text_chunk_similarities**：计算文本块相似性（KNN 图）
- **enable_fulltext_search**：启用全文搜索和混合搜索
- **graph_schema_consolidation**：图谱模式整合

---

## 🔍 Graph RAG 模式详解

### 1. Generate Cypher 模式

- **原理**：AI 根据问题自动生成 Cypher 查询语句
- **适用场景**：需要精确查询图谱结构和关系
- **优势**：查询灵活，可处理复杂图遍历
- **工具**：`GenerateCypherTool`

### 2. Graph Retrieve 模式

- **原理**：基于向量相似度检索相关文档块和实体
- **适用场景**：语义搜索、相似问题推荐
- **优势**：检索速度快，支持语义理解
- **工具**：`GraphRetrieveTool`

### 系统提示词

两个模式使用不同的系统提示词来优化回答质量：

- `GENERATE_CYPHER_GRPAH_RAG_SYSTEM_PROMPT`：Cypher 生成提示
- `GRAPH_RETRIEVE_SYSTEM_PROMPT`：图谱检索提示

---

## 🛠 开发指南

### 前端开发

**启动开发服务器（热重载）：**
```bash
cd frontend
npm run dev
```

**构建生产版本：**
```bash
cd frontend
npm run build
```

**预览生产构建：**
```bash
cd frontend
npm run preview
```

**代码检查（如果配置了 ESLint）：**
```bash
cd frontend
npm run lint
```

**前端目录结构说明：**
- `src/components/` - 可复用的 Vue 组件
- `src/views/` - 页面级组件
- `src/stores/` - Pinia 状态管理
- `src/api/` - API 请求封装
- `src/router/` - 路由配置
- `src/style.css` - 全局样式和 CSS 变量
- `src/dark-theme.css` - 暗色主题覆盖样式

**添加新的页面：**
1. 在 `src/views/` 创建新的 Vue 组件
2. 在 `src/router/index.js` 添加路由
3. 在导航中添加链接（如需要）

**修改主题颜色：**
编辑 `src/style.css` 中的 CSS 变量：
```css
:root {
  --primary-color: #667eea;  /* 主色调 */
  --background: #f7fafc;     /* 背景色 */
  --surface: #ffffff;        /* 表面色 */
  /* ... */
}
```

### 后端开发

#### 添加新的 LLM 模型

在 `.env` 文件中添加：

```bash
LLM_MODEL_<provider>_<model_name>="<model_name>,<api_key>,<base_url>"
```

例如：

```bash
LLM_MODEL_openai_gpt-4="gpt-4,sk-xxx,https://api.openai.com/v1"
```

### 自定义实体提取提示词

编辑 `backend/src/common/prompts.py` 中的提示词模板。

### 扩展数据源

在 `backend/service.py` 的 `extract_graph_from_*` 函数系列中添加新的数据源处理逻辑。

---

## ❓ 常见问题

### Q1：Neo4j 连接失败

**解决方案**：
1. 确认 Neo4j 服务正在运行
2. 检查连接参数（URI、用户名、密码）
3. 确认防火墙未阻止 7687 端口

### Q2：向量索引不存在

**解决方案**：
在 Neo4j Browser 中执行：

```cypher
CALL db.index.vector.createNodeIndex('vector', 'Chunk', 'embedding', 1536)
```

### Q3：LLM API 调用失败

**解决方案**：
1. 检查 API 密钥是否正确
2. 确认 API base URL 可访问
3. 查看账户余额和调用限制

### Q4：文档提取卡住

**解决方案**：
1. 检查文档状态：在 Neo4j Browser 中查询 `MATCH (d:Document) RETURN d.fileName, d.status`
2. 查看后端日志获取详细错误信息
3. 尝试使用 `START_FROM_LAST_PROCESSED_POSITION` 模式继续

### Q5：前端无法连接后端

**解决方案**：
1. 确认后端服务正在运行在 `http://localhost:7860`
2. 检查浏览器控制台的 CORS 错误
3. 确认前端 API 配置正确（`frontend/src/api/graph.js`）
4. 尝试在后端添加 CORS 允许源

---

## 📚 API 文档

详细的 API 文档请访问：

- Swagger UI：`http://localhost:7860/docs`
- ReDoc：`http://localhost:7860/redoc`

### 主要端点

| 端点 | 方法 | 描述 |
|-----|------|------|
| `/health` | GET | 健康检查 |
| `/backend_connection_configuration` | POST | 测试 Neo4j 连接 |
| `/upload` | POST | 分块上传文件 |
| `/extract` | POST | 提取知识图谱 |
| `/chat` | POST | Graph RAG 对话 |
| `/post_processing` | POST | 执行后处理任务 |

---

## 🤝 贡献指南

欢迎贡献！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📝 更新日志

### v2.0.0
- ✅ 全新的 Vue 3 前端应用
- ✅ 现代化的 UI 设计（Element Plus）
- ✅ 暗色/亮色主题切换
- ✅ 实时上传进度显示
- ✅ 响应式布局优化
- ✅ Pinia 状态管理
- ✅ 优雅的聊天界面

### v1.0.0
- ✅ 基础知识图谱提取功能
- ✅ Graph RAG 对话功能
- ✅ 多数据源支持
- ✅ 静态 HTML 测试界面

---

## 📄 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

---

## 🙏 致谢

- [Vue.js](https://vuejs.org/) - 渐进式 JavaScript 框架
- [Element Plus](https://element-plus.org/) - 优秀的 Vue 3 UI 组件库
- [Vite](https://vitejs.dev/) - 下一代前端构建工具
- [LangChain](https://langchain.com/) - 强大的 LLM 应用开发框架
- [Neo4j](https://neo4j.com/) - 优秀的图数据库
- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的 Python Web 框架

---

## 📧 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 Issue
- 发送 Pull Request
- 邮件联系：[your-email@example.com]

---

**Made with ❤️ by Knowledge Graph Builder Team**
