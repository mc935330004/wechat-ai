# wechat-ai

个人微信智能客服独立后端，项目目录 `F:\ideaProject\wechat-ai`。前端目录 `F:\TraeProject\wechat-ai-web`。

## 启动

在项目根目录打开 PowerShell：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

脚本使用本机 `D:\java\jdk-17` 的 JDK 17，执行后恢复当前进程环境；不修改机器或用户级 Java 环境变量。其他机器可通过 `-JavaHome '你的JDK17目录'` 指定路径。IDEA Project SDK、Maven Importer 和 Maven Runner JRE 均使用 JDK 17；修改后重新加载 Maven 项目。

默认地址 `http://127.0.0.1:8080`：

- `GET /api/v1/admin/status`：最小只读状态，模式固定 OFF。
- `GET /actuator/health`：健康检查。未开放环境、配置等敏感 Actuator 端点。

默认只绑定本机，无数据库、无模型调用、无微信读写。正式鉴权和业务能力按后续阶段加入；不要直接改成公网绑定。

## 构建与验证

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 -Action test
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 -Action package
```

打包文件 `target\wechat-ai-0.0.1-SNAPSHOT.jar` 使用 JDK 17 执行 `java -jar`。直接使用 `mvnw.cmd` 时也需将当前终端 JAVA_HOME 设为 JDK 17；本机系统默认 java 仍可能是 Java 8，应优先使用启动脚本。

## POM 配置

默认：Spring Boot 4.1.1、Java 17、Web MVC、Validation、Actuator、配置元数据处理器、DevTools、JUnit/Spring Boot 测试、可执行 jar 插件；Spring AI 2.0.1 BOM 管理 AI 依赖。

按需启用的 Maven profiles：

| profile | 已配置依赖 | 启用条件 |
|---|---|---|
| ai | Spring AI OpenAI starter | 模型/兼容接口、API key 与模型名称已配置 |
| database | JDBC、MySQL 驱动、Flyway 与 MySQL migration 支持 | 本地 MySQL 安装完毕并配置连接信息后启用 |
| rag | Spring AI RAG | 按 RAG 实施阶段选择向量存储，目前不引入 pgvector |

Maven profile 控制可选依赖，默认不启用这些依赖。运行环境默认为 `dev`，无需额外指定 Spring profile。例如模型已配置后：

```powershell
$env:AI_CHAT_PROVIDER = 'openai'
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 -MavenProfiles ai
```

## 配置文件

只保留两份运行配置：

- `src/main/resources/application.yml`：系统配置，包括应用名、默认环境、错误信息隐藏、健康端点范围、AI 默认关闭和迁移保护。
- `src/main/resources/application-dev.yml`：开发环境配置，包括监听地址/端口、日志等级、MySQL 连接参数、模型地址和环境变量引用。

AI 默认关闭。启用聊天需配置 `AI_CHAT_PROVIDER=openai`、`OPENAI_API_KEY`、`OPENAI_MODEL`，可选 `OPENAI_BASE_URL`，并启用 Maven profile `ai`。Embedding 需另设 `AI_EMBEDDING_PROVIDER=openai` 和 `EMBEDDING_MODEL`。

当前尚未安装、连接数据库。MySQL 配置仅预留，默认启动不加载 JDBC，因此不尝试连接 MySQL。以后安装 MySQL 并建立 `wechat_ai` 数据库，配置 `DATABASE_USERNAME`、`DATABASE_PASSWORD`，必要时设置 `DATABASE_URL`，再运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 -MavenProfiles database
```

Flyway 默认关闭，待迁移脚本准备完毕后再设 `FLYWAY_ENABLED=true`。禁止将密码、密钥写进配置文件或提交到 Git。真实数据库和模型连接尚未验证。

## 资料

- `requirements.md`：完整需求基线。
- `docs/contracts/openapi.yaml`：当前已实现 API。
- `docs/acceptance/project-bootstrap.md`：本次创建与运行验证记录。
- `.tools/`、`target/`、日志和运行数据不进 Git。
