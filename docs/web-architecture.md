# Web 展示架构决策

## 1. 决策摘要

项目下一阶段采用 **FastAPI + Jinja2 服务端渲染（SSR）+ SQLite**：

- Web 页面是采集结果的默认查看方式。
- SQLite 是唯一权威业务数据源。
- Excel 不再参与正常采集持久化，仅在用户明确执行导出命令时生成。
- 不迁移当前已有 Excel；首次实施后从空 SQLite 开始积累新数据。
- 第一版不采用 React/Vue SPA，不建设独立前端工程和公开 REST API。

本文件是目标设计，不代表当前代码已经实现 Web 或 SQLite。

## 2. 背景与需求

当前系统已经具备模块化采集、Cookie 管理、`code=37` 恢复、职位筛选和 Excel 增量保存。新的产品目标是让用户通过浏览器查看结果，而不是把 Excel 当作默认界面。

核心交互仅包括：

- 职位列表、筛选、排序和分页；
- 职位详情和 BOSS 原始链接；
- 采集批次与错误状态；
- 按需导出 Excel。

系统主要由个人在本机或 Tailscale 网络内使用，数据更新频率低，不需要多用户实时协作。

## 3. 方案比较

### 3.1 服务端渲染

```text
Browser → FastAPI Route → Query Service → SQLite
                       → Jinja2 Template → HTML
```

优点：

- 单一 Python 工程和单一部署单元；
- 不需要 Node.js、前端构建链、CORS 和客户端状态管理；
- GET 查询参数天然适合筛选、排序、分页、收藏和前进/后退；
- 页面默认可在无 JavaScript 时工作；
- 安全边界简单，浏览器不接触 Cookie、stoken 或内部采集接口；
- 现有应用层、领域层和基础设施层可直接复用。

不足：

- 极复杂交互和高频局部更新不如 SPA 灵活；
- 如果未来要支持独立移动端，需要补 JSON API。

### 3.2 前后端分离

```text
Browser SPA → JSON API → Application Service → SQLite
```

优点：

- 适合独立前端团队、移动端复用和大量客户端状态交互；
- 对复杂实时仪表盘和高度动态界面更灵活。

当前代价：

- 增加 Node.js、React/Vue、API schema、CORS、两套测试和两套发布流程；
- 筛选与分页仍由后端 SQLite 完成，SPA 只是增加 JSON 和客户端渲染层；
- 当前没有独立 App、公共 API、多用户实时协作或复杂写操作，收益不足。

## 4. 决策

第一版采用服务端渲染：

```text
FastAPI + Jinja2 + 原生 CSS + 少量原生 JavaScript
```

不采用：

```text
React/Vue SPA + 独立 REST API + Node.js 构建工程
```

核心功能不得依赖 JavaScript。JavaScript 只用于清空筛选、复制链接、移动端筛选面板等体验增强。

## 5. 未来演进条件

只有以下实际需求出现时才重新评估前后端分离：

- 独立移动端、桌面端或浏览器扩展需要复用 API；
- 多用户实时交互；
- 大量局部无刷新写操作；
- 高度动态的数据可视化仪表盘；
- 前端由独立团队维护；
- 对外提供稳定公共 API。

即使未来增加 JSON API，也应复用应用服务：

```text
Jinja2 Routes ─┐
               ├→ Application Services → SQLite Repository
JSON API ──────┘
```

## 6. 第一版 Web 边界

页面：

- `GET /`：跳转 `/jobs`；
- `GET /jobs`：职位列表、筛选、排序、分页；
- `GET /jobs/{job_id}`：职位详情；
- `GET /runs`：采集批次；
- `GET /health`：只检查应用和数据库，不请求 BOSS。

第一版不实现：

- Web 上传 Cookie、编辑配置或启动采集；
- 自动投递、自动沟通；
- WebSocket、SPA、公开 API；
- 注册登录、多用户权限；
- 在线删除或编辑职位。

## 7. 部署模型

同一个 Python 包提供两个命令，运行成两个进程：

```text
boss-zhipin web       # 长期运行，只读展示
boss-zhipin collect   # 定时执行，写 SQLite
```

共享数据库：

```text
var/data/boss-zhipin.sqlite3
```

SQLite 启用 WAL 与 busy timeout，使 Web 读取和采集写入可安全共存：

```sql
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
```

Web 默认监听 `127.0.0.1`。绑定 Tailscale IP 必须显式配置；不默认绑定 `0.0.0.0`，不通过 Funnel 暴露。

## 8. 相关文档

- [Web 数据与页面设计](web-data-and-ui.md)
- [Web 实施路线](web-implementation-roadmap.md)
- [安全设计](security.md)
- [测试策略](testing.md)
