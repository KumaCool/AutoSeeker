# 工程化改造文档索引

本目录描述 `boss-zhipin-iv8` 的已实现工程架构，以及下一阶段 Web 默认展示的目标设计与实施路线。

> 当前状态：CLI 模块化重构已经完成；SQLite、Web 展示和按需 Excel 导出仍处于方案阶段。旧 Excel 不迁移。

## 文档

- [架构设计](architecture.md)：目标边界、模块职责、依赖方向和运行流程。
- [配置设计](configuration.md)：配置模型、覆盖顺序、路径和敏感信息处理。
- [运维设计](operations.md)：安装、执行、定时任务、日志、失败恢复与验收。
- [安全设计](security.md)：Cookie、日志脱敏、文件权限和人工验证边界。
- [测试策略](testing.md)：单元、契约、集成和真实站点验收。
- [开发指南](development.md)：开发环境、离线验收、运行数据和提交规则。
- [实施路线](refactoring-roadmap.md)：按阶段拆分的任务、验收标准和提交策略。
- [Web 架构决策](web-architecture.md)：服务端渲染与前后端分离的比较、决策和边界。
- [Web 数据与页面设计](web-data-and-ui.md)：SQLite schema、查询、页面和按需 Excel 导出。
- [Web 实施路线](web-implementation-roadmap.md)：从 SQLite 主存储到 SSR Web 和部署的阶段任务。

## 核心原则

1. 采用模块化单体、稳定 CLI 和服务端渲染 Web，不引入微服务、任务队列或独立 SPA。
2. 源码与运行时数据分离；Cookie、日志、缓存、浏览器 Profile 和 Excel 不进入版本控制。
3. 先补测试再迁移职责；下一阶段从空 SQLite 开始，不迁移旧 Excel。
4. 领域逻辑不依赖 HTTP、iv8 或 openpyxl。
5. 真实站点测试必须显式触发，不进入默认 CI，也不绕过验证码或人工安全验证。
6. 每个最小任务独立验证、独立 Git commit；每个阶段完成后整体回归并等待批准。
