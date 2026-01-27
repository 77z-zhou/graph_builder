# 🚀 快速启动指南

## 一键启动（推荐）

### Windows 用户

```bash
# 1. 启动后端服务
cd backend
python app.py

# 2. 新开一个终端，启动前端服务
cd frontend
python start_server.py
```

### Mac/Linux 用户

```bash
# 1. 启动后端服务
cd backend
python app.py

# 2. 新开一个终端，启动前端服务
cd frontend
python3 start_server.py
```

浏览器会自动打开测试页面：`http://localhost:8000/test.html`

---

## 手动启动

### 方式 1: 使用 Python HTTP 服务器

```bash
cd frontend
python -m http.server 8000
# 然后访问: http://localhost:8000/test.html
```

### 方式 2: 直接打开 HTML 文件

⚠️ **可能遇到 CORS 问题，不推荐**

直接双击 `frontend/test.html` 文件在浏览器中打开。

---

## ✅ 启动检查清单

在开始测试之前，请确保：

- [ ] Neo4j 数据库正在运行
  - 检查方式：访问 `http://localhost:7474`
  - 默认端口：7474 (HTTP), 7687 (Bolt)

- [ ] 后端服务已启动
  - 访问：`http://localhost:7860/health`
  - 应返回：`{"healthy": true}`

- [ ] 前端服务已启动
  - 访问：`http://localhost:8000/test.html`
  - 应看到测试页面界面

---

## 🎯 第一次测试流程

### 1. 测试数据库连接

1. 在测试页面填写 Neo4j 连接信息
2. 点击 "🔍 测试连接"
3. 确认状态显示 "已连接 ✅"

### 2. 上传测试文件

1. 选择一个测试文档（PDF/TXT/DOCX）
2. 选择模型（DeepSeek 或 Qwen）
3. 点击 "🚀 上传文件"
4. 等待上传完成（100%）

### 3. 提取知识图谱

1. 确认文件名已自动填充
2. 调整提取参数（可选）
3. 点击 "⚗️ 提取知识图谱"
4. 等待处理完成

### 4. 查看结果

- 在 Neo4j 浏览器中查看：`http://localhost:7474`
- 运行查询：`MATCH (n) RETURN n LIMIT 25`

---

## 📁 测试数据

可以使用 `data/` 目录下的示例文件进行测试：

- `Apple stock during pandemic.pdf`
- `LLM Comparisons with one pdf.docx`

---

## 🛠️ 常见问题

### Q1: 点击按钮没有反应？

**A:** 按 F12 打开浏览器开发者工具，查看 Console 和 Network 标签，检查是否有错误信息。

### Q2: CORS 错误？

**A:** 确保使用 `python start_server.py` 启动前端，而不是直接打开 HTML 文件。

### Q3: 连接数据库失败？

**A:**
1. 检查 Neo4j 是否运行：`http://localhost:7474`
2. 验证连接信息是否正确
3. 查看 backend 终端是否有错误日志

### Q4: 提取超时？

**A:**
- 减小 "Token 块大小" 参数
- 检查网络连接
- 查看 LLM API 是否正常

---

## 📞 获取帮助

如果遇到问题：

1. 查看后端终端日志
2. 查看浏览器开发者工具（F12）
3. 查看 `frontend/README.md` 详细文档
4. 查看后端 `CLAUDE.md` 了解系统架构

---

## 🎉 开始使用

现在你已经准备好了！点击测试页面上的按钮开始测试你的知识图谱构建器吧！

祝你测试顺利！ 🚀
