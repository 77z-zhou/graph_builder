# 知识图谱构建器前端 - Knowledge Graph Builder Frontend

基于 Vue 3 + Vite + Element Plus 的现代化前端项目

## 📋 功能特性

- ✨ **Vue 3** - 使用最新的 Vue 3 Composition API
- 🚀 **Vite** - 极速的开发体验
- 🎨 **Element Plus** - 优秀的 Vue 3 UI 组件库
- 📦 **Pinia** - Vue 3 官方推荐的状态管理
- 🔄 **Vue Router** - 官方路由管理器
- 💬 **Graph RAG Chat** - 与知识图谱对话功能

## 🛠️ 技术栈

- **框架**: Vue 3.4+
- **构建工具**: Vite 5.2+
- **UI 组件**: Element Plus 2.7+
- **状态管理**: Pinia 2.1+
- **路由**: Vue Router 4.3+
- **HTTP 客户端**: Axios 1.6+
- **CSS 预处理**: 原生 CSS (支持 CSS Variables)

## 📦 安装依赖

```bash
cd frontend-vue
npm install
```

## 🚀 开发

```bash
npm run dev
```

应用将在 `http://localhost:3000` 启动

## 🏗️ 构建

```bash
npm run build
```

构建产物将输出到 `dist` 目录

## 📁 项目结构

```
frontend-vue/
├── public/                 # 静态资源
├── src/
│   ├── api/               # API 接口
│   │   └── graph.js      # 图谱相关 API
│   ├── assets/           # 资源文件
│   ├── components/       # 公共组件
│   │   └── ChatPanel.vue # 聊天面板组件
│   ├── router/           # 路由配置
│   │   └── index.js      # 路由定义
│   ├── stores/           # Pinia 状态管理
│   │   ├── neo4j.js      # Neo4j 连接状态
│   │   └── documents.js  # 文档状态管理
│   ├── views/            # 页面组件
│   │   ├── Layout.vue    # 主布局
│   │   └── Dashboard.vue # 仪表盘页面
│   ├── App.vue           # 根组件
│   ├── main.js           # 入口文件
│   └── style.css         # 全局样式
├── index.html            # HTML 模板
├── package.json          # 项目配置
├── vite.config.js        # Vite 配置
└── README.md             # 项目说明
```

## 🔧 配置说明

### 环境变量

创建 `.env.local` 文件配置环境变量：

```bash
# API 基础 URL
VITE_API_BASE_URL=http://localhost:7860
```

### API 代理

在 `vite.config.js` 中已配置代理，开发环境下 `/api` 请求将转发到后端服务器：

```javascript
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:7860',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, '')
    }
  }
}
```

## 📝 核心功能说明

### 1. Neo4j 连接管理

- 配置并测试 Neo4j 数据库连接
- 连接状态实时显示
- 配置信息保存在 Pinia store 中

### 2. 文件上传

- 支持拖拽上传
- 5MB 分块上传大文件
- 实时上传进度显示
- 支持 PDF, TXT, DOCX 等格式

### 3. 知识图谱提取

- 支持多种数据源：本地文件、网页 URL、Bilibili、Wikipedia
- 可配置提取参数
- 提取进度实时反馈

### 4. Graph RAG 聊天

- 与知识图谱进行对话
- 流式响应显示
- 消息历史记录

## 🎨 样式自定义

项目使用 CSS 自定义属性（CSS Variables）定义主题颜色，可在 `src/style.css` 中修改：

```css
:root {
  --primary-color: #667eea;
  --primary-dark: #5568d3;
  --background: #f7fafc;
  --surface: #ffffff;
  /* ... 更多变量 */
}
```

## 🔗 后端 API 对接

确保后端服务运行在 `http://localhost:7860`，或修改 `.env.local` 中的 `VITE_API_BASE_URL`。

主要 API 端点：

- `POST /backend_connection_configuration` - 测试 Neo4j 连接
- `POST /upload` - 文件上传
- `POST /extract` - 知识图谱提取
- `POST /chat` - Graph RAG 聊天

## 📱 浏览器支持

- Chrome >= 87
- Firefox >= 78
- Safari >= 14
- Edge >= 88

## 🤝 开发建议

1. **组件开发**: 遵循单一职责原则，保持组件简洁
2. **状态管理**: 合理使用 Pinia stores，避免过度使用全局状态
3. **API 调用**: 统一使用 `src/api` 目录下的封装方法
4. **样式编写**: 优先使用 Element Plus 组件样式，必要时自定义
5. **代码规范**: 建议使用 ESLint 进行代码检查

## 📄 许可证

MIT
