# Tests

本目录包含完全离线的 pytest/unittest 测试，覆盖领域筛选、配置、Cookie、HTTP 契约、stoken、Excel、CLI 和项目结构。

默认测试不得读取真实 `var/secrets/cookies.json`，也不得访问 BOSS。真实站点验收必须单独、显式执行。
