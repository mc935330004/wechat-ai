# 项目创建与启动验收

日期：2026-10-04（Asia/Shanghai）。

## 工程

- 后端：F:\ideaProject\wechat-ai。
- 前端：F:\TraeProject\wechat-ai-web。
- 当前 Java 17.0.10（原创建时为 Java 21.0.12.1），Spring Boot 4.1.1，Spring AI BOM 2.0.1，Maven Wrapper 3.9.15。
- Node 22.23.3，Vue 3.5.43，Vite 8.3.2，TypeScript 5.9.3。
- 两个本地 Git 仓库已初始化，无远程推送；工具压缩包、依赖、构建与运行数据均忽略。

## 实际验证

| 验证 | 结果 |
|---|---|
| 后端 scripts/dev.ps1 -Action package | PASS，含实际 HTTP 集成测试与可执行 jar 打包 |
| 初次创建时 mvnw.cmd -Pai,database,rag dependency:resolve -DincludeScope=runtime | PASS，当时 AI/PostgreSQL/Flyway/pgvector/RAG 依赖解析成功；后续数据库选型已改为按需 MySQL，未连接真实服务 |
| BootstrapHttpTest | 1 测试，0 failures/errors；状态 OFF、健康 UP、未暴露 actuator/env |
| 前端 scripts/dev.ps1 -Action test | PASS，正常 OFF、错误 schema 与 HTTP 503 校验 |
| 前端 scripts/dev.ps1 -Action build | PASS，TypeScript + Vite 构建 |
| npm audit --omit=dev --audit-level=high | PASS，生产依赖 0 vulnerabilities（本次检查） |
| java -jar 启动可执行 jar | PASS，127.0.0.1:8080 |
| GET /api/v1/admin/status | 200，appName=wechat-ai，status=UP，effectiveMode=OFF，schemaVersion=1 |
| GET /actuator/health | 200，status=UP |
| 前端开发服务 | PASS，127.0.0.1:5173 |
| 经前端 /api 代理读取后端 | PASS，同一 OFF 状态契约 |
| Chrome 无头浏览器连接页 | PASS，显示后端已连接/OFF，无 pageerror |
| 模拟后端 503 → 重新检查恢复 | PASS，异常提示明确、可恢复 |
| 375px 窄屏 | PASS，无横向溢出 |

实际打包文件：target\wechat-ai-0.0.1-SNAPSHOT.jar。截图在本次聊天输出目录 `wechat-ai-web-初始化.png`。

## 启动与结束

两个项目根目录均可执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

后端脚本使用本机 D:\java\jdk-17；前端脚本使用 Node 22。IDE 的运行 JDK/Node interpreter 同样应选择相应版本，避免系统旧 Java 8/Node 10 导致启动失败。

本次验证后两个服务留在本机运行。终端启动的服务可 Ctrl+C 结束；本次验证实例的 PID 保存于各项目 runtime 目录。结束该实例前按端口/PID核对目标，不停止其他项目的服务。

## 范围与回退

本次只创建与验证基础工程。未访问微信，未自动发送消息，未验证真实模型/数据库/RAG，不代表完整 Phase 0 或生产就绪。

外部依赖采用显式 Maven profiles，运行环境默认为 dev；未启用外部依赖时保持无密钥/无数据库默认启动。回退外部功能时关闭相应 Maven profiles 与模型开关，回到默认 OFF。完整需求与后续执行入口在 requirements.md / docs/phases/phase-00.md。

## 配置整理复验（2026-10-04）

- 只保留 application.yml（系统配置）和 application-dev.yml（开发环境参数）；删除 application-database.yml、application-rag.yml。
- 默认运行环境 dev，AI 默认关闭；数据库依赖按需启用，MySQL 尚未安装，因此未连接数据库。
- database profile 改为 MySQL Connector/J 与 Flyway MySQL，移除 PostgreSQL/pgvector 依赖；向量存储待 RAG 阶段选择。
- mvnw.cmd clean package：PASS，原有 HTTP 集成测试 1 项通过；清理后打包只包含两份配置。
- scripts/dev.ps1 -Action resolve -MavenProfiles database：PASS，仅验证依赖解析。
- 重启可执行 jar：PASS，127.0.0.1:8080；健康 UP、模式 OFF、前端 /api 代理正常。

## Java 17 切换复验（2026-10-04）

- 使用用户已有 Oracle JDK 17.0.10（D:\java\jdk-17），POM java.version=17。
- 启动脚本固定使用 JDK 17 并校验编译器版本，支持 -JavaHome 指定其他安装目录；不修改全局环境变量。
- IDEA 注册 JDK 17，项目语言级别/SDK、Maven Importer/Runner 配置为 17；IDE 打开时需重新加载 Maven 项目刷新配置。
- 测试的 HttpClient 不再使用 Java 21 的 AutoCloseable API。
- 清理后使用 JDK 17 编译、HTTP 集成测试和打包：PASS；主类字节码 major version=61。
- 使用 JDK 17 启动 jar：PASS；运行进程确认来自 D:\java\jdk-17\bin\java.exe，健康 UP、模式 OFF、前端代理正常。
