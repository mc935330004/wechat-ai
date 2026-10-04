# 个人微信 PC + RPA/UI Automation + Spring AI 智能客服系统

## 需求规格与 Codex 分阶段实施指南

- 文档版本：1.1（已纳入独立新项目与实际创建路径）
- 编写与资料核查日期：2026-10-03（Asia/Shanghai）
- 目标实施方式：由 Codex 完成代码、接口、迁移、测试、运行脚本和交付文档；人负责微信登录、客户身份核实、业务资料授权、真实环境验收与上线模式选择。
- 适用范围：单 Windows 交互桌面、单个人微信账号、少量固定白名单客户、中文私聊客服。
- 当前状态：需求设计完成；本文不表示任何本机微信兼容性测试已经通过。
- 后端新项目：`wechat-ai`，根目录 `F:\ideaProject\wechat-ai`。
- 前端新项目：`wechat-ai-web`，根目录 `F:\TraeProject\wechat-ai-web`。
- 工程关系：前后端分离，独立目录、依赖、构建与 Git 仓库；`mc-ai` 是用户另一个项目，不在本项目中编写或修改，也不作为实施前置条件。
- 项目创建：第一阶段即 Phase 0，先创建两个最小可运行工程与安全默认配置，再进行桌面可行性验证；2026-10-04 已完成两个基础工程创建、构建与连通；微信能力探测尚未执行，完整 Phase 0 状态见 docs/phases/phase-00.md。
- 推荐底座：`Hello-Mr-Crab/pywechat` 的 `pyweixin`，通过适配器依赖；最终是否采用由 Phase 0 的本机证据决定。
- 默认模式：`OFF`；联调与试运行切到 `DRAFT`；满足 Phase 7、Phase 10 门槛后，按客户与意图逐项启用 `AUTO`。

> 核心原则：先验证 UI 能力，再做业务闭环；先草稿，再自动发送；先确认联系人，再写输入框；发送结果不确定时转人工核对，不自动补发。UI Automation/OCR 不等于微信官方开放接口，也不能保证账号不被限制。禁止采用 Hook、DLL 注入、逆向协议、数据库解密或以规避平台风控为目的的仿生操作。

## 目录

1. [项目目标与范围](#1-项目目标与范围)
2. [技术选型与复用边界](#2-技术选型与复用边界)
3. [总体架构与目录结构](#3-总体架构与目录结构)
4. [核心行为规格](#4-核心行为规格)
5. [API 与事件契约](#5-api-与事件契约)
6. [数据模型与持久化](#6-数据模型与持久化)
7. [Phase 0—10 实施计划](#7-phase-010-实施计划)
8. [测试与最终验收](#8-测试与最终验收)
9. [部署、运行与回滚](#9-部署运行与回滚)
10. [Codex 工作规则与提示词](#10-codex-工作规则与提示词)
11. [交付清单与待确认项](#11-交付清单与待确认项)
12. [资料来源与事实边界](#12-资料来源与事实边界)

---

## 1. 项目目标与范围

### 1.1 业务目标

系统读取白名单客户发来的文本和可转写语音，将连续消息合并为一个问题，由 Spring AI 结合知识库和受控业务工具生成有证据的答复，按模式展示草稿或经安全校验自动发送，并保存可追溯的处理记录。

主要场景：

1. 客户咨询产品、材料、服务流程，系统从授权知识库回答。
2. 客户询问指定品类、地区、规格的行情，系统调用已授权数据源，标注时间、单位和来源。
3. 客户询问自己项目的采购或成本影响，系统只访问与该客户绑定的项目。
4. 客户连续发送文本或语音，系统合并语义后只生成一份有效答复。
5. 运营人员审阅、修改、批准或丢弃草稿，随时接管会话。
6. 订阅客户在指定时间收到行情摘要；每个任务和收件人独立校验、去重。

### 1.2 范围分级

| 优先级 | 能力 | 完成阶段 |
|---|---|---|
| P0 | 创建 wechat-ai / wechat-ai-web、最小启动与本机微信能力报告 | 0（第一阶段） |
| P0 | 工程、契约、认证、持久化、FakeAdapter | 1 |
| P0 | 白名单私聊监听、方向识别、去重、断线补交 | 2 |
| P0 | 连续消息聚合、语音转文字、人工接管 | 3 |
| P0 | Spring AI、DRAFT、草稿审阅台 | 4 |
| P0 | RAG 及来源、项目权限隔离 | 5 |
| P0 | MarketTool、ProjectTool、确定性成本计算 | 6 |
| P0 | ReplyPolicy、SendGuard、AUTO、急停 | 7 |
| P1 | 定时行情、订阅、任务幂等 | 8 |
| P1 | OCR 读取降级与受控草稿 | 9，UIA 不可用时前移验证 |
| P0 | 监控、备份、部署、全流程验收 | 10 |

完整交付包括 P0、P1。若 OCR 在目标环境不能可靠识别，允许以“功能受限、禁止自动发送”交付明确限制，不能将该能力验收为通过。第一轮实用版本可在 Phase 4 以 DRAFT 上线试用，但不算完整项目完成。

### 1.3 明确不做

- 不修改微信程序，不 Hook，不注入 DLL，不读取进程内存，不逆向个人微信网络协议。
- 不读取/解密微信内部数据库、缓存或加密语音文件；自己系统的 SQLite/PostgreSQL 不在此限制内。
- 不用 HID、鼠标仿生轨迹、真人击键分布、故意错字、随机无关操作、假装离线等规避检测方案。
- 不做批量加好友、群控、群发营销、朋友圈自动运营；第一版不处理群聊自动答复。
- 不自动登录、扫码、绕过验证码、自动解封或反复重登。
- 不让模型直接操作微信、决定收件人、执行任意 SQL、访问任意 URL 或写业务数据。
- 不自动承诺价格、合同条款、付款、退款、投资收益；行情答复以数据说明为限。
- 不承诺读取全部历史或捕获离线期间所有消息；可读取范围由 UI 能力决定。
- 不默认支持图片/文件/视频理解、语音发送、多账号、多桌面和无人值守锁屏操作。

### 1.4 必须满足的约束

| 编号 | 要求 |
|---|---|
| R-01 | 仅已核实的白名单私聊进入业务处理，账号变化立即失效所有联系人绑定 |
| R-02 | 只有 `IN` 消息触发问答，`OUT/UNKNOWN/SYSTEM` 不触发 |
| R-03 | 接收可重试，但同一逻辑消息不能重复创建业务答复；不能把重复文本直接当重复消息 |
| R-04 | 每个会话串行聚合，语音转写更新原消息，不新建一条文本消息 |
| R-05 | 回复必须绑定 batch、会话版本、联系人绑定版本和策略版本 |
| R-06 | 未完成 SendGuard 不允许向微信输入框写入，也不允许发送 |
| R-07 | 模型输出不是权限依据；收件人、数据权限和模式由应用代码确定 |
| R-08 | 所有发送有唯一 commandId、持久化本地日志和可核对回执 |
| R-09 | 发送结果 `UNCERTAIN` 禁止自动重试，即使后端回执丢失 |
| R-10 | 急停、接管、注销、身份冲突、锁屏、版本变化使待发送指令失效 |
| R-11 | 缺证据、Tool 失败、语音不完整、OCR 歧义降级草稿或人工，不编造事实 |
| R-12 | 启动、升级、故障恢复默认 OFF；AUTO 不随进程重启自动恢复 |
| R-13 | 原始聊天、截图、业务资料按授权处理，日志默认脱敏并设保留期限 |
| R-14 | 所有阶段保存真实验收证据，未执行的真人桌面测试不能写“通过” |

### 1.5 初始容量与质量目标

- 初始上限：1 个账号、10 个已绑定私聊；Phase 0 先验证 2 个测试会话。超过可见或可验证范围应排队并告警，不盲目扫描。
- 聚合安静窗口 4 秒、最长聚合窗口 15 秒；语音转写等待上限另计，见 4.4。
- 单回复最大 800 个 Unicode 字符，默认不拆成多条；超限生成短草稿。
- 正常网络与选定模型下，从 batch 就绪到草稿生成 p95 ≤ 30 秒；语音等待与人工审阅时间单独计量。
- 目标测试集内：错发 0、重复 UI 发送 0、发给非白名单 0、接管后自动发送 0。该目标是发布门槛，不是对所有未来环境的绝对保证。
- Phase 0 连续 4 小时；Phase 10 DRAFT 连续 24 小时和受控 AUTO 8 小时，真实时长必须记入报告。

## 2. 技术选型与复用边界

### 2.1 推荐技术栈

| 层 | 选择 | 决策与约束 |
|---|---|---|
| 微信桌面 | 正常安装的 Windows 微信 PC | 人工登录；记录完整版本、语言、DPI、桌面会话 |
| Agent | Python 3.12 x64 候选，venv | 上游虽写 Python ≥3.10，实际以锁定 commit 的安装测试为准 |
| UIA 底座 | `pyweixin` / pywinauto | 固定包版本或 Git commit；不能直接调用上游 AutoReply 跳过本系统策略 |
| Agent 通信 | httpx + Pydantic | Agent 主动向后台 HTTP 上报/取指令，第一版不开放 Agent 入站端口 |
| Agent 持久化 | SQLite WAL | 自有 inbox/outbox/游标/发送日志；敏感数据受文件 ACL 保护 |
| Java | JDK 17 LTS、Maven Wrapper | 新建 wechat-ai，groupId 候选 com.wechat、artifactId=wechat-ai、基础包 com.wechat.ai |
| 后端 | Spring Boot + Spring AI BOM | 新工程验证 Spring AI 2.0.x + Boot 4.0.x/4.1.x 的确切稳定版本；Phase 0 锁 Boot，Phase 1 锁兼容 AI BOM，禁止混搭 |
| 对话/Embedding | Spring AI provider adapter | 服务商、模型和数据区域配置化；模型无 Tool Calling 时走确定性路由 |
| 业务数据库/向量库 | PostgreSQL + pgvector + Flyway | 同一库保存业务状态与事务 outbox，向量隔离按 metadata + 服务端权限 |
| 任务调度 | Spring 调度 + PostgreSQL 任务表 | 单服务起步；数据库唯一键/锁处理幂等，第一版无需引入 Quartz/Redis/Kafka |
| 运维指标 | Actuator + Micrometer；可选 Prometheus | 只开放受认证的管理网络；不把聊天内容放指标标签 |
| 操作台 | Vue 3 + TypeScript + Vite | 新建 wechat-ai-web，独立 package.json、锁文件、构建与部署；Node 版本按选定 Vite 官方 engines 锁定 |
| OCR | PaddleOCR 本地候选 | 独立可选依赖组；验证 Windows CPU 安装、中文精度与运行成本 |
| 测试 | pytest、JUnit 5、Testcontainers、Playwright | 非桌面测试在 FakeAdapter 中；真实 UI 测试只能在 Windows 交互桌面 |

上述版本是选型范围，Phase 0 先记录两个工程的基础版本，Phase 1 完成确切的 `docs/dependency-lock.md`：每个版本、来源、SHA/包哈希、许可证、兼容矩阵、升级方法。不能在代码里使用 `latest` 或无版本生产依赖。Spring AI 的 Boot 兼容关系及 BOM 以[官方入门页](https://docs.spring.io/spring-ai/reference/getting-started.html)为依据；整个项目独立建设，不升级或修改 mc-ai。

前端初始化方式与 Node 兼容条件以 [Vue Quick Start](https://vuejs.org/guide/quick-start.html)和 [Vite Getting Started](https://vite.dev/guide/)核实；生成器也要固定版本。环境不满足时记录缺项，不能把安装命令失败解释为项目已创建成功。

### 2.2 GitHub 参考项目

| 项目与链接 | 已核实用途 | 本项目采用方式 | 必须补齐的能力 |
|---|---|---|---|
| [Hello-Mr-Crab/pywechat](https://github.com/Hello-Mr-Crab/pywechat) | `pyweixin` 提供导航、消息、联系人、监听等桌面封装 | 首选 RPA 底座，封装为 `PyweixinAdapter`，Phase 0 决定是否准入 | 稳定内部身份、去重、重启恢复、策略、SendGuard、发送不确定状态 |
| [ai4evt/wechat-ai-reply](https://github.com/ai4evt/wechat-ai-reply) | 截图/OCR/消息解析/发送分层 | 参考 OCR 边界与稳定帧思路；不运行其整套自动发送 | 不能只按文本 MD5 去重；补齐身份核实、输入保护、权限、人工回退 |
| [LTEnjoy/easyChat](https://github.com/LTEnjoy/easyChat) | UIA 微信助手、定时发送、搜索联系人、版本适配 | 只研究定时任务与搜索错发案例；不作为主后台 | 不照搬第一搜索项发送、群发、防掉线或随机间隔功能 |
| [cluic/wxauto](https://github.com/cluic/wxauto) | UIAutomation 参考，README 有生产/商业用途限制说明 | 阅读思路，不作为生产依赖；具体代码复用前核实授权 | 不沿用旧客户端假设 |
| [cluic/wxauto4](https://github.com/cluic/wxauto4) | 当前 README 标注停止更新 | 不选为新项目主底座 | 无 |
| [spring-projects/spring-ai](https://github.com/spring-projects/spring-ai) | ChatClient、RAG、Tool 框架 | 直接依赖，使用与 BOM 对应的文档 | 业务权限、证据校验、失败处理和评估集 |
| [pgvector/pgvector](https://github.com/pgvector/pgvector) | PostgreSQL 向量检索扩展 | 直接使用 | 文档生命周期和权限过滤 |
| [PaddlePaddle/PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) | OCR 引擎 | 可选依赖，不自研 OCR 模型 | 微信区域裁剪、方向判断、身份与重复文本处理 |

核查补充：

- 上游[微信 4.1+ 说明](https://github.com/Hello-Mr-Crab/pywechat/blob/main/Weixin4.0.md)明确存在 UI 可见性问题，不能承诺任意账号可用。Issues 中的故障报告仅是用户反馈，不能据此推断因果关系或封号概率。
- [QuickStart](https://github.com/Hello-Mr-Crab/pywechat/blob/main/QuickStart.md)记录的安装发行名是 `pywechat127`，模块导入名与发行名不同；Phase 0 复核锁定版本包含的 `pyweixin`。不要凭项目名执行 `pip install pyweixin`。
- 上游 `pywechat` 的 [LICENSE](https://github.com/Hello-Mr-Crab/pywechat/blob/main/LICENSE)标注 LGPL 2.1；分发前检查锁定版本的完整文件与附加说明，列出版权、修改与依赖清单。分进程/HTTP 封装只是工程边界，不能当作自动免除许可证义务的依据。
- OCR 参考项目 README 中“零风险”“任意版本即用”等宣传不作为需求依据。easyChat README 记录了 2026-09-15 的 4.1.15 适配与搜索错发修复，仅说明该项目的记录，不保证本系统兼容。
- 不复制参考项目的密钥、配置、提示词或不需要的控制逻辑；不安装其 Skill/MCP 来获得绕过本系统发送入口的能力。

### 2.3 哪些直接用，哪些自己开发

| 能力 | 直接复用 | 自主开发 |
|---|---|---|
| 窗口定位、导航、控件读取 | 经验证的 pyweixin 方法 | 能力探测、版本封装、身份验证 |
| UI 输入/发送 | 经验证的 UI 底层操作 | 单 UI actor、SendGuard、持久化发送状态机 |
| 消息监听 | 可用的 Monitor/控件观察能力 | 方向过滤、快照对齐、逻辑 ID、持久游标 |
| 语音转文字 | 微信正常 UI 提供的转写功能（若可用） | 语音定位、转写关联、等待/失败状态 |
| 模型、Embedding、向量操作 | Spring AI + pgvector | ReplyService、权限、评估、来源校验 |
| Tool 框架 | Spring AI Tool API | 行情适配、项目授权、输入 schema、成本计算 |
| OCR 引擎 | PaddleOCR | 截图区域、稳定帧、身份冲突与草稿回退 |
| 调度/指标/数据库 | Spring、Micrometer、PostgreSQL | 订阅幂等、失约处理、告警规则、审计 |
| 模式/接管/审阅 | 无可直接替代的底座 | OFF/DRAFT/AUTO、ReplyPolicy、wechat-ai-web |

## 3. 总体架构与目录结构

### 3.1 系统分层

```text
Windows 交互桌面（人工登录个人微信）
  微信 PC
    ↕ 正常 UI Automation；必要时屏幕区域 OCR
  Python RPA Agent
    Adapter / IdentityResolver / WindowValidator
    Listener → SnapshotAligner → Local Inbox / Cursor
    VoiceConverter / UiActor / SendGuard / SendJournal
    HTTP Client / Local Emergency Stop / Heartbeat
    ↕ 带认证的 HTTP、至少一次事件交付、幂等指令
Spring Boot / wechat-ai（业务状态权威）
  Gateway → Normalizer → Durable Inbox → Aggregator
  IntentRouter → RoutePlan → RAG / ToolExecutor
  Spring AI → EvidenceValidator → ReplyPolicy
  Reply Draft / Command Outbox / Scheduler / Audit
    ↕
PostgreSQL + pgvector                  管理操作台
  消息、批次、草稿、命令、权限、任务        草稿、接管、模式、订阅、运行状态
```

职责规则：

- Agent 负责桌面事实，不持有模型服务密钥，不决定业务客户权限，不把屏幕识别结果当官方微信 ID。
- 后端负责模式、白名单、权限、AI、草稿、任务与指令；不远程执行任意 Agent 脚本。
- UI 的所有激活、切会话、菜单、转写、输入、发送通过一个 `UiActor` 串行执行。不要多线程同时操作微信。
- 模型只产生内容与建议意图；Tool 执行前后均由代码校验。发送是后端和 Agent 的确定性状态机。
- PostgreSQL 事务 inbox/outbox 保证业务更新与指令一致；Agent SQLite 保存断线队列与发送证据。HTTP 重试不意味着 UI 动作重试。
- 管理台只访问后端，不直接连接 Agent/模型。第一版单运营角色，敏感项目可增设审批角色。

### 3.2 两个独立项目的实际目录

```text
F:\ideaProject\wechat-ai\                # 后端 Git 仓库与 Maven 根
├── AGENTS.md / README.md / requirements.md
├── pom.xml / mvnw / mvnw.cmd / .mvn/
├── src/main/java/com/wechat/ai/
│   ├── WechatAiApplication.java
│   └── wechat/{gateway,identity,message,aggregate,ai,rag,tool,policy,send,schedule,admin,audit}/
├── src/main/resources/
│   ├── db/migration/
│   ├── prompts/
│   └── application-example.yml
├── src/test/{java,resources}/
├── agent/                              # Python RPA，独立 venv/依赖；不参与 Maven 打包
│   ├── pyproject.toml / requirements.lock / config.example.yaml
│   ├── src/wechat_agent/
│   │   ├── adapters/{base,fake,pyweixin,ocr}.py
│   │   ├── ui/{actor,identity,window_validator}.py
│   │   ├── receive/{listener,aligner,cursor,voice}.py
│   │   ├── transport/{client,outbox}.py
│   │   ├── send/{guard,journal,executor}.py
│   │   ├── storage/migrations/
│   │   └── {config,health,main}.py
│   ├── tools/probe.py
│   └── tests/{unit,contract,replay,windows}/
├── docs/
│   ├── adr/                            # 新工程选型，不涉及 mc-ai 修改
│   ├── contracts/openapi.yaml           # 全系统唯一接口规范源
│   ├── contracts/schemas/
│   ├── phases/phase-00.md ... phase-10.md
│   ├── dependency-lock.md / compatibility.md
│   ├── security-and-retention.md
│   ├── operations/runbook.md
│   └── acceptance/
├── test-fixtures/{messages,ui-snapshots,ocr,rag,tools}/
├── scripts/{dev-up,verify,backup,restore,agent-start}.ps1
├── deploy/{compose.yml,windows-task-template.xml,.env.example}/
└── .gitignore

F:\TraeProject\wechat-ai-web\            # 前端独立 Git 仓库与 npm 根
├── AGENTS.md / README.md / .gitignore
├── package.json / package-lock.json
├── index.html / vite.config.ts / tsconfig.json
├── .env.example                        # API 地址，绝不含模型或 Agent 密钥
├── src/
│   ├── main.ts / App.vue
│   ├── api/                            # 生成 DTO/client + 请求封装
│   ├── views/                          # 模式、会话、草稿、资料、命令、订阅
│   ├── components/
│   └── router/
├── tests/{unit,e2e}/
├── docs/{contract-version.json,phase-notes/}
└── dist/                               # 构建产物，不进 Git
```

目录简写规则：后续 `docs/`、`scripts/`、`deploy/`、`test-fixtures/` 相对后端根目录；`agent/` 相对后端根，Python 源模块写为 `agent/src/wechat_agent/...`；`Java/<模块>` 表示 `F:\ideaProject\wechat-ai\src\main\java\com\wechat\ai\wechat\<模块>`；`wechat-ai-web/...` 相对前端根。不存在额外的 `backend/` 或 `admin-ui/` 嵌套工程。

前后端独立联调规则：

- 开发候选后端端口 8080、前端 5173（占用时改配置并记录）；Vite `/api` 代理到后端，生产前端独立发布并反向代理 `/api`，不使用通配 CORS。
- 后端 OpenAPI 为接口真值；前端从其确切版本生成 DTO/client，并记录 schema hash/contractVersion；不手工维护互相冲突的两份 API 定义。
- 前端不依赖后端相邻目录、硬编码盘符或符号链接来构建。本地生成器通过显式参数定位后端契约，CI 使用版本化契约文件/制品；构建产物本身不包含本地绝对路径。
- 两个仓库分别维护锁文件、README、AGENTS.md 与提交。后端保存统一阶段报告，记录两个仓库的 commit/schema hash；前端保存对应阶段变更摘要，便于跨项目续接。
- 以 F: 路径执行创建前确认盘符/父目录、工具版本和权限。若目标目录存在则先读取并保留，不删除、不覆盖已有项目、不执行破坏性初始化；缺 F: 或创建权限时只报告实际阻塞，不私自换路径。
- Git 初始化仅在目标工程目录进行，不在 `F:\ideaProject` 或 `F:\TraeProject` 父目录初始化；不创建远程仓库、不自动推送。

运行数据 `runtime/`、密钥配置、SQLite、原图、未脱敏聊天、模型缓存均不进 Git。测试夹具必须脱敏或合成。

### 3.3 Agent 自有适配接口

```python
class WechatAdapter(Protocol):
    def probe(self) -> CapabilityReport: ...
    def account_snapshot(self) -> AccountObservation: ...
    def open_conversation(self, binding: ContactBinding) -> ChatSnapshot: ...
    def read_snapshot(self, binding: ContactBinding) -> ChatSnapshot: ...
    def transcribe_voice(self, ref: MessageRef) -> TranscriptResult: ...
    def input_snapshot(self) -> InputSnapshot: ...
    def fill_input(self, text: str) -> FillResult: ...
    def press_send(self) -> UiActionResult: ...
    def observe_sent(self, expected: SentExpectation) -> SendObservation: ...
```

这是本项目定义的接口，不是上游 API 声明。Codex 必须检查锁定上游代码后实现映射；不确定的方法先写 FakeAdapter 和 `UNSUPPORTED`，不得编造方法名。

## 4. 核心行为规格

### 4.1 OFF / DRAFT / AUTO 与接管

| 模式 | 监听/保存 | AI | 微信输入 | 微信发送 |
|---|---|---|---|---|
| OFF | 可配置本地健康检查；默认暂停聊天读取，上报健康和模式 | 停止新任务，取消未完成回复 | 禁止 | 禁止，包括人工批准的系统指令 |
| DRAFT | 已授权白名单 | 生成并保存在管理台 | 默认禁止；点击“填入微信”可经 Guard 填入 | 仅人工在微信发送，或管理台明确单次批准后经 Guard 发送 |
| AUTO | 已授权白名单 | 生成 | 满足 ReplyPolicy 与 SendGuard 后 | 满足所有门槛后发送；不满足则草稿/人工 |

模式按“全局 → Agent/账号 → 联系人”限制计算：OFF 优先、DRAFT 次之、AUTO 最后，任一层限制不能被更低层放宽。`manualApproval` 只授权一份绑定内容的单次发送，可在 DRAFT 下使用；不把联系人切到 AUTO，不绕过 OFF、接管、身份与过期检查。

独立运行状态：`READY / PAUSED / DEGRADED / DISCONNECTED / LOCKED / ACCOUNT_CHANGED`。即使配置为 AUTO，只要不 READY 就禁止动作。管理台展示配置模式和有效模式及降级原因。

人工接管：`takeover=true` 阻止 AI 新任务、取消草稿自动批准与待发命令，UI actor 释放窗口。默认接管不自动超时；人员主动恢复后进入 DRAFT，需要重新校验才能 AUTO。检测到不匹配系统发送记录的 OUT 消息、用户修改输入框或 UI 操作冲突，保守转接管。不能保证仅靠 UI 观察识别所有人工作业，因此共用桌面默认 DRAFT；AUTO 推荐专用交互桌面。

### 4.2 账号与联系人身份

- `accountKey/contactKey/conversationKey` 为本系统生成的不可变 UUID，不是声明拿到微信官方内部 ID。
- 人首次在正常 UI 核实账号和好友，绑定可见备注、资料页中可验证字段、私聊类型与可观察特征，保存 `bindingVersion` 和证据摘要。
- 搜索字符串只是导航线索。不能默认第一项，不模糊匹配、不把群名当好友，不单独靠头像或聊天标题确认。
- 昵称重复、备注变化、资料不可读、账号无法核实：`IDENTITY_AMBIGUOUS`，禁止 AUTO；人工重新绑定。
- 微信登录账号变化时，Agent sessionEpoch 变化，所有旧指令与绑定失效，重新做本机能力/身份验证。
- 如果 UI 只提供一个不唯一标题，不能宣称完成独立双重身份校验；该联系人仅允许管理台草稿、人工选择与人工发送。

### 4.3 消息监听与去重

监听次序：能力探测 → 授权白名单 → 观察可读会话/未读提示 → 串行读取快照 → 方向分类 → 快照对齐 → SQLite 提交 → 后端上报 → 后端落库确认。

策略：

1. 未读数字仅用于提醒读取，不能当消息内容或数量真值；未读状态被人工清掉仍应通过已绑定会话快照对齐发现消息。
2. 启动首次快照建立 baseline，默认历史仅归档、不触发回答；重启从持久游标对齐，无法确认的新旧边界标为 `GAP/AMBIGUOUS`，进入人工审阅。
3. 不假设 UIA RuntimeId 跨重启稳定。优先可验证的 provider ID；否则用会话、方向、类型、可观察时间、上下文锚点与出现序号做序列对齐。
4. `eventId` 在本地首次捕获时生成并持久化，HTTP 重试复用；`logicalMessageId` 在快照对齐后生成，同一消息重复观察复用。
5. 内容哈希用于辅助比对，不能作为唯一去重键。例如连续两个“好的”或相同长度语音必须保留两个位置。
6. 后端唯一约束 `(agentId,eventId)` 抗传输重复，`(accountKey,conversationKey,logicalMessageId)` 抗重复捕获；修订版本单独去重。
7. 入站方向不确定时禁止调用 AI；系统发送回声归为 OUT，并与 send journal 对齐，避免自我回复循环。
8. 会话滚动、加载旧消息、撤回、编辑、语音显示转写导致布局变化不得解释为新消息。找不到锚点先标 gap，不无界滚动补历史。
9. 队列有界、优先按会话公平处理；饱和告警并暂停 AUTO，不丢掉未确认事件。网络断开期间 SQLite 保存，后端恢复后幂等补交。
10. 无法读取的窗口/未展示会话明确记 `UNOBSERVABLE`。本系统不保证完整历史覆盖；管理台显示最近成功观察时间和 gap。

### 4.4 连续消息聚合与语音

聚合键：`(accountKey,conversationKey)`。仅聚合同一联系人 IN 消息，禁止跨客户共享上下文。

- 第一条 IN 建立 OPEN batch；每条新消息推后静默截止至最后到达后 4 秒，最晚不超过首条后 15 秒。
- 同一会话由数据库版本和串行 worker 处理；后台时间用 UTC Instant，展示/任务用 Asia/Shanghai。
- batch 最多 20 条、合并文本最多 4000 字符；超限拆批并转 DRAFT，不连发多份自动答复。
- 未转写语音进入 `PENDING`，先占据消息序位，再更新同一 logicalMessageId 的 revision。
- 语音优先读取微信自动转写；否则在原语音 UI 元素仍能准确定位时调用正常右键菜单转写。功能缺失不强行猜坐标。
- 每条语音最长等待 30 秒；一个 batch 等待未完成语音最长 45 秒。到期转 `PARTIAL_REVIEW`，不以已知部分自动回答。
- 转写字段保留 provider、status、可观察置信度；微信不提供置信分就用 null，不虚构 0.99。
- 金额、数量、日期、品类歧义即便转写完成仍进入 DRAFT/澄清；语音文字不是可信业务事实。
- 迟到转写更新原记录、使原草稿过期；需要人工再生成。不得自动发送第二份修正答复。
- 仅有人工正常导出/提供且已授权的音频时才允许可选 ASR。第一版不以抓取微信缓存或回环录音作自动 fallback；转写失败转人工。
- 生成过程中收到新 IN，conversationRevision 增加：尚未发送的草稿/命令过期，合并未答消息重新处理；已确认发出的消息归入下一轮。持续新消息导致多次取消时转人工，避免无限模型重算。

### 4.5 AI、RAG 与证据

输入由三部分组成：受信系统策略、已授权会话内容（不受信数据）、已过滤 RAG/Tool 证据（不受信数据）。客户、文档或 Tool 结果中的“忽略规则”“发给另一个人”等文本不改变权限。

路由类型：`FAQ / MARKET_QUERY / PROJECT_QUERY / PROJECT_IMPACT / SMALL_TALK / HUMAN_REQUIRED / UNSUPPORTED`。RoutePlan 使用 schema 校验、枚举与最大调用预算，不接收可执行代码。

RAG：

- 导入授权 Markdown/TXT/PDF/DOCX，先验证大小、格式；复杂扫描 PDF 不自动默认为已成功抽取。
- 文档记录版本、有效期、权限域、来源与校验哈希；分块候选 500–800 tokens，重叠 80–120 tokens，按选定模型实际 tokenizer 调整。
- 初始 topK=5，阈值通过评估集校准，禁止将任一 similarity score 当业务真实性概率。
- 项目/客户权限在检索前强制过滤，在返回后再次检查；模型不能传入/覆盖权限过滤条件。
- 回复内部保存 documentId/chunkId/version、引用片段摘要与 EvidenceRef；给客户显示简短来源说明，不能泄露内部路径或未授权材料。
- 无有效来源、互相冲突、过期、检索失败：转草稿/人工；不得凭模型常识回答公司事实、当前行情或项目数据。
- 删除/撤权同步使向量、缓存、未发送草稿失效；更换 embedding 模型/维度需要新索引与验证，不混合旧新向量。

复用 Spring AI 的检索/Advisor 基础能力；权限、版本和证据规则由本系统实现。参见[Spring AI RAG 官方文档](https://docs.spring.io/spring-ai/reference/api/retrieval-augmented-generation.html)。

### 4.6 Tool 与确定性计算

允许工具：`market_quote`、`project_summary`、`project_cost_impact`；全部只读。模型调用前，后端从可信 contactKey 解析客户和允许项目；不从模型参数接受 accountKey/customerId 的授权判断。

MarketQuote 至少包含：品类、地区、规格、价格、货币、单位、税/运费口径、来源、asOf、fetchedAt、有效期、真实数据或 fixture 标记。缺品类/规格/地区需澄清；不同口径不可直接相减。

ProjectSummary 至少包含：projectId、授权客户、剩余采购量及单位、基准价格和日期、可公开字段、资料版本。客户不能根据“我是某项目负责人”自授权限。

成本影响由 Java BigDecimal 计算：

```text
deltaCost = (currentComparableUnitPrice - baselineUnitPrice)
            × remainingQuantity
```

仅在单位、币种、规格、含税/运费口径可比时计算；存储四舍五入规则与输入快照，不由 LLM 心算。给客户明确这是基于指定采购量和价格口径的情景测算。

每个 Tool 超时候选 5 秒；一个问答最多 3 次调用，总预算 15 秒。幂等只读请求可有限重试；权限拒绝、参数错误不重试。服务商、凭证和行情使用授权尚未确认时用 fixture 完成代码与测试，fixture 结果标记 `NOT_FOR_LIVE_SEND`、不可通过 AUTO。

使用 Spring AI `@Tool`/ToolCallback 与可信 ToolContext 的具体方式由锁定版本决定；应用强制授权，参见[官方 Tool 文档](https://docs.spring.io/spring-ai/reference/api/tools.html)。

### 4.7 ReplyPolicy

ReplyPolicy 是 Java 确定性规则，返回 `BLOCK / DRAFT / AUTO_ELIGIBLE / HUMAN_REQUIRED` 和 reasonCodes。

AUTO 必须同时满足：

- 有效 AUTO、账号与联系人白名单、无接管、能力满足、消息方向清楚。
- batch 完整、新鲜、最新 conversationRevision；没有读取 gap 和身份歧义。
- 意图位于 AUTO 允许列表（初始仅已验证 FAQ 和标准行情事实查询）。
- 每个事实有有效、已授权证据；无 fixture、过期行情或矛盾来源。
- 无敏感信息、承诺、付款、合同、投诉、重大项目成本决策；PROJECT_IMPACT 初始一律 DRAFT。
- 回复内容满足 schema、长度、格式与数字核对；不得含内部凭证、系统提示词、恶意链接。
- 业务时间、订阅/会话授权、频率与预算均通过。

模型自报“高置信度”不能批准 AUTO。未通过规则保留可解释的草稿或人工工单。语音来源和 OCR 来源默认 DRAFT；语音只有通过单独评估与联系人授权后才可逐项放宽。纯 OCR 身份仍不满足 AUTO 条件。

### 4.8 SendGuard 与防错发

禁止将底座“找好友并直接发送”的一体方法作为无检查入口。发送拆成导航、读取身份、填入、核对、提交、观察几个受控步骤。

1. 后端创建唯一 commandId，绑定 account/contact/conversation、bindingVersion、replyRevision、contentHash、policyVersion、conversationRevision、agentSessionEpoch、失效时间。
2. Agent 取指令并写本地 journal；所有微信 UI 操作占用同一 UiActor 和桌面级互斥锁，不能有第二发送进程。
3. 检查本地急停、有效模式、接管、桌面会话、登录账号、版本/DPI、在线授权、指令 TTL、目标私聊及身份。
4. 检查导航前原输入框。任何未归属系统的内容、光标/窗口异常都不覆盖，转人工；导航前后均须检查。
5. 导航目标，重新检查精确身份与输入框为空；无法确认即阻断，不默认第一个搜索结果。
6. 从后端 authorize-fill 获取绑定当前目标、空输入、内容与版本的短期填入许可，保存本地 FILL_INTENT，复核后填入批准内容；不通过剪贴板自动发送。若用剪贴板粘贴需保护外部剪贴板变化，不能覆盖用户新复制内容。
7. 读取实际输入文本，计算 canonical UTF-8/NFC/SHA-256 哈希并核对目标、内容、当前会话版本。不能只校验模型原文本而不读输入框。
8. 向后端申请一次性短期 commit token；后端再次检查模式、授权、版本、新 IN、内容和指令状态。离线不发。
9. Agent 保存 `COMMIT_INTENT` 并 flush/fsync 后，在无网络等待的最小动作区间再次检查本地急停/窗口/输入/身份，执行发送一次。最终检查失败则 `BLOCKED`，不继续。
10. 观察对应 OUT 气泡、目标会话、内容及发送失败标识；只看到输入框清空不足以证明成功。记录证据等级与回执。

状态：

```text
QUEUED → CLAIMED → PREPARED → COMMIT_AUTHORIZED → COMMIT_INTENT
                                                    ↓
                                 CONFIRMED / FAILED / UNCERTAIN
任意未触发 UI 发送的阶段 → BLOCKED / EXPIRED / CANCELLED
```

`CONFIRMED` 仅表示 UI 已观察到目标会话的匹配消息，不能证明收件人已收到/已读。`FAILED` 仅用于已证明未执行发送的情况；触发后出现错误、断网、未观察到匹配或进程崩溃均为 `UNCERTAIN`。历史同内容气泡不能当新成功证据，需要发送前后尾部增量与位置匹配。

恢复规则：

- `COMMIT_INTENT` 之后未得到明确确认，重启时一律 UNCERTAIN，不重新按 Enter。
- 重复 claim/commit/receipt 只返回已保存状态；commit token 已发行但回包丢失，不重新授权一次新发送机会。
- UNCERTAIN 只能人工查看微信后通过 reconcile 标为“已观察发送”或“证实未发送”；后者若需补发，应生成新的经人工批准的 command，保留关联和理由。
- 填入后失败，仅当当前目标及内容仍完全归属该 command 时才可清理；发生人工编辑或身份变化时保留并接管，不能误删用户内容。
- 全局 OFF 在数据库提交时撤销未提交指令；管理台同时传递急停，Agent 本地热键立即设置内存停止标志并持久化。已发生的 UI 发送不能撤回。
- 数据库事务与微信 GUI 之间不能获得严格分布式原子性。commit token 候选有效期 2 秒，最终检查到按键尽可能短；远程 OFF 与最终按键竞态仍有极小窗口，必须在验收与运行说明中披露，不宣称绝对即时阻断。
- 固定业务限速候选：同会话间隔 ≥30 秒、每联系人 ≤10 次/小时、账号 ≤30 次/小时，默认全部可调低；目的为避免骚扰、控制负载与事故范围，不保证平台允许或用于伪装真人。超额转草稿，不延迟堆积自动发。

### 4.9 定时行情

- 仅人工登记且同意接收的 contactKey 订阅，记录品类、地区、规格、时区、时段、取消状态。
- 配置固定业务时刻，例如 Asia/Shanghai 工作日 09:00；节假日/交易日必须使用已确认业务日历，未配置时暂停任务，不猜测。
- 每个触发时刻 materialize 一个 `schedule_run`；唯一 `(subscriptionId,scheduledFor)`，生成独立回复并通过同一 Policy/Guard。
- 行情快照按一致来源与时刻共用，收件人权限和发送命令分别生成。通知包含数据截至时间，不把历史值标“当前”。
- 静默期、OFF、DRAFT、取消订阅、过期数据、失败任务、接管均阻止 AUTO；DRAFT 只生成计划草稿。
- misfire 默认 SKIP：恢复时不补发过期行情；默认 run 10 分钟有效（按业务配置调整）。不发送积压日报。
- 定时推送与客户入站竞争时，暂停推送并优先会话回复；人接管不触发任何自动推送。

### 4.10 OCR fallback

OCR 是读取能力降级，不是规避 UI 可见性限制的方法，不保证任何版本可用。

- 捕获微信窗口内已授权聊天区域，避免全屏收集其他应用；保存窗口边界/DPI/区域版本。
- 两次稳定帧确认文字与气泡位置；利用边界、方向、顺序、上下文锚点对齐，不能只按文字 hash 去重。
- OCR score 只反映识别分数；初始阈值 0.95 待评估，联系人、方向、金额、日期关键字段仍需校验。
- 标题与资料不可独立核实或有重名时，停止自动导航/输入，仅生成管理台草稿或请求人工粘贴消息。
- OCR 模式第一版禁 AUTO 和无人批准的定时发送；UIA 的身份/输入/发送校验仍可用时，允许人工单次批准经同一 Guard 发送。纯 OCR 无法核实目标时由人正常在微信发送。
- UIA/OCR 观察同一会话时共享 logicalMessageId 对齐器，切换不重复处理；切换模式需新 baseline、能力降级事件和待发取消。
- 窗口移动、缩放、遮挡、多屏、输入法弹窗、聊天滚动或布局变化使区域配置失效；暂停、重新校准，不继续盲点坐标。

### 4.11 日志与数据保护

日志关联链：`traceId → eventId → messageId → batchId → replyId → commandId → receiptId`。日志保存阶段状态、耗时、错误码、版本和证据摘要；正文默认不打印。

业务内容确需持久化时进入受控数据库，管理台按角色访问；截图默认不落盘，事故证据可启用加密/ACL 与自动清理。候选保留：脱敏运行日志 30 天、聊天业务记录 30 天、失败截图 7 天、审批/发送审计 90 天；上线前由业务负责人确定，并同步清理向量、缓存、备份生命周期。

密钥通过环境/凭证存储配置，不进 Git、不在报告回显；Agent token 与运营登录分开，模型密钥只在后端。审计包含操作者、模式变化、白名单变更、批准内容 hash、接管、取消及 reconcile 理由。

## 5. API 与事件契约

### 5.1 全局约定

- `/api/v1/agents/**` 仅 Agent Bearer token 可访问；token 绑定 agentId/accountKey/允许操作域，sessionEpoch 在注册后由服务端认可。
- `/api/v1/admin/**` 使用独立运营登录与角色；浏览器 Cookie 会话启用 CSRF 防护、严格 CORS，同源部署优先。
- 第一版 Agent 主动拉取指令，后端无需向 Windows 开放入站控制端口；开发同机可 loopback，跨机 HTTPS 与网络 ACL。
- JSON UTF-8；ID 为字符串 UUID；时间为带 UTC `Z` 的 ISO 8601；Decimal 用字符串，字段须带单位；本地时间只用于展示和排期。
- 用 OpenAPI 3.1 + JSON Schema 明确 required、枚举、长度、范围、未知字段处理；`schemaVersion=1`，不兼容版本拒绝，不默认猜测。
- POST 幂等请求以稳定 Idempotency-Key + 请求 hash 落库；同 key 同 payload 返回原结果，同 key 不同 payload 返回 409。
- 传输超时可退避重试，但事件确认必须在数据库 commit 后发出；UI 发送只能按 command 状态执行一次。
- 管理操作携带 `expectedVersion`，并发版本不匹配 409，不覆盖较新的批准/接管/配置。
- HTTP：400 schema，401 未认证，403 无权限，409 版本/状态冲突，422 业务条件不满足，429 限流，503 依赖不可用。
- 错误统一 `{errorCode,message,traceId,retryable,details}`；details 不包含聊天原文、凭证或完整 UI 树。

### 5.2 Agent API

| 方法/路径 | 请求核心字段 | 响应/语义 | 首次阶段 |
|---|---|---|---|
| POST `/api/v1/agents/register` | agentId、clientVersion、capabilities、accountObservationHash | sessionEpoch、有效配置、configVersion；不自动批准新账号身份 | 1 |
| POST `/api/v1/agents/{id}/heartbeat` | sessionEpoch、desktopState、uiState、capabilityVersion、queueDepth、lastObservedAt | desiredMode、policyVersion、cancelBeforeEpoch；10 秒候选间隔 | 1 |
| GET `/api/v1/agents/{id}/configuration` | configVersion/ETag | 白名单绑定与策略快照，不含模型 key | 2 |
| POST `/api/v1/agents/{id}/events:batch` | events[]，每批 ≤100 | 每 event 的 ACCEPTED/DUPLICATE/REJECTED；允许部分确认，Agent 仅清理已确认项 | 2 |
| GET `/api/v1/agents/{id}/commands?waitSeconds=15` | sessionEpoch | 候选指令列表；读取不等于授权发送 | 4/7 |
| POST `/api/v1/agents/{id}/commands/{cid}/claim` | sessionEpoch、localJournalState | commandVersion、leaseExpiresAt；重复返回既有领取状态 | 7 |
| POST `/api/v1/agents/{id}/commands/{cid}/authorize-fill` | leaseVersion、replyHash、identityEvidence、currentInputHash、chatRevision、guardResults | 短期一次填入许可；复核在线模式/批准/版本/TTL；不返回发送权限 | 7 |
| POST `/api/v1/agents/{id}/commands/{cid}/prepared` | leaseVersion、identityEvidence、inputHash、chatRevision、guardResults | 填入后读回匹配为 PREPARED 或阻断；不返回发送权限 | 7 |
| POST `/api/v1/agents/{id}/commands/{cid}/commit` | expectedVersion、sessionEpoch、inputHash、identityEvidenceHash | 一次性 commitToken、tokenExpiresAt；原子冻结授权内容 | 7 |
| POST `/api/v1/agents/{id}/commands/{cid}/receipts` | receiptId、status、journalStage、observedAt、evidenceHash、errorCode | 保存 UI 结果；重复回执幂等 | 7 |

heartbeat 不意味着有发送授权。连续 30 秒未见心跳，后端暂停新发命令；Agent 获取不了有效在线 commit 时禁止发送。OFF 下注册/心跳仍可进行。

### 5.3 管理 API

| 方法/路径 | 功能与关键约束 | 阶段 |
|---|---|---|
| GET `/api/v1/admin/status` | 展示有效模式、能力、队列、依赖、gap 和最近观察时间 | 1/4 |
| POST `/api/v1/admin/runtime/mode` | scope、targetId、mode、expectedVersion、reason；AUTO 需后端检查准入 | 1/7 |
| POST `/api/v1/admin/runtime/emergency-stop` | 全局 OFF、版本推进、撤销未提交命令、审计 | 7 |
| POST `/api/v1/admin/contacts/bindings` | 人工核实后创建 contactKey 与证据、accountKey、私聊类型 | 2 |
| PATCH `/api/v1/admin/contacts/{key}` | 白名单、回复意图、项目授权；更新 bindingVersion 并撤销旧草稿/命令 | 2/6 |
| GET `/api/v1/admin/conversations/{key}/messages` | 授权访问、分页、方向/转写/gap 标记 | 2/4 |
| POST `/api/v1/admin/conversations/{key}/takeover` | enabled、expectedVersion、reason；恢复默认 DRAFT | 3 |
| GET `/api/v1/admin/replies?status=DRAFT` | 草稿列表、来源、降级原因、原问题与过期状态 | 4 |
| PATCH `/api/v1/admin/replies/{id}` | 人工编辑、expectedVersion；增加 revision，取消旧批准 | 4 |
| POST `/api/v1/admin/replies/{id}/approve` | revision、contentHash、action=`FILL_ONLY/SEND_ONCE`、expectedVersion | 4/7 |
| POST `/api/v1/admin/replies/{id}/discard` | 取消草稿和未提交指令，记录原因 | 4 |
| POST `/api/v1/admin/knowledge/documents` | 授权域/文件，异步导入 jobId；不接受任意外部 URL 下载 | 5 |
| GET `/api/v1/admin/knowledge/jobs/{id}` | 抽取/切块/Embedding/索引状态及错误 | 5 |
| DELETE `/api/v1/admin/knowledge/documents/{id}` | 撤权并作废索引、缓存及相关未发草稿 | 5 |
| POST `/api/v1/admin/tools/diagnostics` | 只读 Tool 测试，运营权限和确定性参数，不触发微信发送 | 6 |
| POST `/api/v1/admin/subscriptions` | 联系人、条件、排期、时区、同意记录、有效期 | 8 |
| PATCH `/api/v1/admin/subscriptions/{id}` | 暂停/取消/改排期，expectedVersion | 8 |
| GET `/api/v1/admin/schedule-runs` | 任务与每个收件人的执行状态、过期/失败原因 | 8 |
| POST `/api/v1/admin/commands/{cid}/reconcile` | 人工观察结论、证据、reason；不隐式重发 | 7/10 |
| GET `/api/v1/admin/audits` | 分页按 trace/command 查审计，独立权限 | 10 |

Phase 4 的 `FILL_ONLY/SEND_ONCE` 都返回 `FEATURE_NOT_ENABLED`，直至 Phase 7 实现并验收完整 Guard；不能先留下绕过 Guard 的填入/发送后门。Phase 7 的 FILL_ONLY 先完成 claim 和身份/空输入校验，向 authorize-fill 获取短期在线许可，保存本地填入意图后再检查并写入；随后读回核对、prepared、FILLED 回执并进入人工接管，不申请发送 commit、不按发送键。重复填入命令不能覆盖后续人工修改；写入后崩溃/不确定转人工，不重复填。

### 5.4 消息事件样例

```json
{
  "schemaVersion": 1,
  "eventId": "evt-example-001",
  "eventType": "MESSAGE_OBSERVED",
  "agentId": "agent-example",
  "sessionEpoch": 7,
  "accountKey": "account-example",
  "contactKey": "contact-example",
  "conversationKey": "conversation-example",
  "bindingVersion": 3,
  "logicalMessageId": "message-example-001",
  "messageRevision": 1,
  "direction": "IN",
  "messageType": "VOICE",
  "content": null,
  "source": "UIA",
  "observedAt": "2026-10-03T01:20:05Z",
  "displayedAt": null,
  "captureOrdinal": 152,
  "identityStatus": "VERIFIED",
  "transcript": {"status": "PENDING", "provider": "WECHAT_UI", "confidence": null},
  "evidence": {"snapshotHash": "sha256-placeholder", "alignmentStatus": "NEW"},
  "traceId": "trace-example-001"
}
```

样例 ID/hash 为可读占位值，实际 schema 要求合法 UUID/SHA-256。语音成功发 `MESSAGE_UPDATED`，沿用 logicalMessageId、messageRevision=2、content=转写文本、transcript.status=SUCCEEDED；不新建入站文本事件。displayedAt 无法可靠识别时为 null，不用 observedAt 假冒客户实际发送时间。

其他事件：`HUMAN_OUT_OBSERVED / CAPABILITY_CHANGED / IDENTITY_AMBIGUOUS / READ_GAP / DESKTOP_LOCKED / ACCOUNT_CHANGED / LOCAL_STOP`。按 schema 独立 payload，不能向后端发送任意命令。

### 5.5 回复与命令样例

```json
{
  "replyId": "reply-example",
  "revision": 2,
  "batchId": "batch-example",
  "conversationRevision": 19,
  "contactKey": "contact-example",
  "intent": "MARKET_QUERY",
  "text": "截至指定来源时间，该地区指定规格报价为……。",
  "evidenceRefs": [{"type": "TOOL", "refId": "quote-example", "asOf": "2026-10-03T01:00:00Z"}],
  "policyDecision": "DRAFT",
  "reasonCodes": ["MODE_DRAFT"],
  "fixture": false,
  "contentHash": "sha256-placeholder",
  "status": "DRAFT",
  "expiresAt": "2026-10-03T01:25:00Z"
}
```

```json
{
  "commandId": "command-example",
  "type": "SEND_REPLY",
  "agentId": "agent-example",
  "accountKey": "account-example",
  "contactKey": "contact-example",
  "conversationKey": "conversation-example",
  "agentSessionEpoch": 7,
  "bindingVersion": 3,
  "conversationRevision": 19,
  "replyId": "reply-example",
  "replyRevision": 2,
  "content": "已经审阅的完整内容",
  "contentHash": "sha256-placeholder",
  "policyVersion": 8,
  "authorizationKind": "MANUAL_ONCE",
  "approvalId": "approval-example",
  "createdAt": "2026-10-03T01:21:00Z",
  "expiresAt": "2026-10-03T01:23:00Z"
}
```

命令类型还包括 `FILL_DRAFT`，其专用终态为 `FILLED`，不能转换成发送成功；后续人工在微信发送记 OUT/人工接管。默认草稿 TTL 5 分钟，发送命令 2 分钟、领取 lease 30 秒、commit token 2 秒，均可配置且被内容有效期收紧。长期业务草稿可保留供阅读，但过期后必须重新生成/校验才能批准。

## 6. 数据模型与持久化

### 6.1 PostgreSQL 核心表

ID 使用 UUID，时间使用 timestamptz，金额/数量使用带单位的 numeric，不用 float。状态字段用 enum/check 约束；可检索字段建立索引；每个可变聚合使用 version 乐观锁。模型对话记忆与消息事实存储分离，不能用 ChatMemory 替代审计数据库。

| 表 | 主要字段 | 约束/索引与用途 |
|---|---|---|
| agent | id、client_version、session_epoch、capabilities、last_heartbeat、runtime_state | id 主键；账号注册关系受管理授权 |
| account_binding | account_key、agent_id、observation_hash、verified_at、binding_version、status | 身份变化不能修改成另一人，撤销后新建 |
| contact_binding | contact_key、account_key、display_alias、identity_evidence、binding_version、whitelist、status | account+内部 key 唯一；显示名不唯一 |
| customer_contact | contact_key、customer_id、authorized_project_ids、consent_ref | 显式授权，权限变更带版本与审计 |
| conversation | conversation_key、contact_key、type、revision、takeover、mode_override、last_observed_at、gap_state | 私聊限定；每次新消息/接管推进 revision |
| event_inbox | agent_id、event_id、payload_hash、received_at、processing_state | unique(agent_id,event_id)；原子接受与消息更新 |
| message | message_id、logical_message_id、conversation_key、direction、type、content、observed_at、displayed_at、ordinal、revision、source | unique(account_key,conversation_key,logical_message_id) |
| message_revision | message_id、revision、content、transcript_status、evidence_hash | unique(message_id,revision)；保留转写历史 |
| aggregate_batch | batch_id、conversation_key、conversation_revision、status、opened_at、quiet_due_at、hard_due_at、voice_due_at | 可恢复 OPEN/WAITING_VOICE/READY；同会话串行 |
| batch_member | batch_id、message_id、message_revision、position | 单条原始 IN 只进入一个当前有效 batch，重算保留旧关系并作废旧版本 |
| reply | reply_id、batch_id、revision、text、content_hash、intent、policy_decision、reasons、evidence_refs、status、expires_at | unique(batch_id,reply_generation_version)；DRAFT/STALE/APPROVED/SENT 等 |
| reply_approval | approval_id、reply_id、reply_revision、content_hash、operator_id、action、approved_at | 单次授权，不按联系人泛化；编辑作废旧批准 |
| send_command | command_id、reply_id、reply_revision、authorization_kind、versions、status、lease、expires_at、commit_token_hash | commandId 幂等；一份有效回复+动作只有一条活跃命令 |
| send_receipt | receipt_id、command_id、status、journal_stage、evidence、observed_at | receipt_id 唯一；不接受终态回退，矛盾回执进入审计 |
| transaction_outbox | id、type、aggregate_id、payload、available_at、delivered_at、attempts | 与 reply/command 更新同事务写入，worker 幂等处理 |
| knowledge_document | document_id、version、source_ref、hash、acl_scope、effective_from/to、status | unique(document_id,version)，撤权立即禁检索 |
| knowledge_chunk | chunk_id、document_id、version、position、text、metadata、embedding | 文档 hash/version 防重复导入；embedding 固定维度 |
| tool_call | call_id、batch_id、name、validated_args、auth_scope_hash、result_ref、status、latency | 不记录明文凭证，调用预算关联 batch |
| market_snapshot | quote_id、品类/地区/规格、price、currency、unit、口径、source、as_of、expires_at、fixture | 查询口径与时间复合索引，过期显式标记 |
| project_snapshot | id、project_id、version、authorized_customer、remaining_quantity、unit、baseline_price、日期 | 只读快照可追溯，字段白名单 |
| subscription | id、contact_key、query_spec、schedule、timezone、consent_ref、status、version | 无同意记录不启用 |
| schedule_run | id、subscription_id、scheduled_for、expires_at、status、reply_id | unique(subscription_id,scheduled_for)，misfire 状态 |
| runtime_policy | scope、target_id、mode、policy_json、version、updated_by | 全局/账号/联系人限制合成 |
| audit_event | id、trace_id、operator、action、target、before/after_hash、reason、created_at | append-only 应用权限，内容默认脱敏 |

不得将上游控件对象 pickle 序列化到数据库；只保存可验证的本系统值和摘要。证据关联结构必须支持撤权导致草稿失效。

### 6.2 Agent SQLite

| 表 | 用途 | 恢复行为 |
|---|---|---|
| capture_cursor | account/conversation、baseline、anchor、ordinal、session_epoch | 重启对齐，失败生成 gap |
| local_message | logical ID、原序位、revision、观察证据 | 更新语音，不重复生成 ID |
| event_outbox | eventId、payload/hash、attempts、next_attempt_at、acked_at | 按 eventId 重发直到后端落库确认 |
| command_journal | commandId、payload_hash、状态、commit_intent_at、证据 | COMMIT_INTENT 之后未确认则 UNCERTAIN |
| command_receipt_outbox | receiptId、commandId、payload、acked_at | 回执补交不重复执行 GUI |
| local_policy | policy_version、emergency_stop、last_valid_config | 离线不自动发送，重启 OFF |

SQLite 的 COMMIT_INTENT 要在 UI 副作用前同步落盘；测试包括磁盘满、写入失败、进程退出。无法保证日志持久化即禁止发送。

### 6.3 一致性与并发

- Gateway 一个事务：去重 inbox → 创建/更新 message → 增加 conversationRevision → 更新聚合任务 → 写 outbox → commit → ACK。
- READY batch 锁定后生成 generationVersion，模型执行在事务外；完成时比较 conversationRevision，过期结果保存为 STALE 不创建活跃发送命令。
- 批准事务比较 replyRevision/contentHash/会话与绑定/有效模式，写 approval + command + outbox；不能先发送再补落库。
- commit 事务再次校验并推进状态，token 与内容不可变绑定；后端 lease 到期不会重新派发可能已执行的 command。
- 同账号 GUI 一个 actor；同会话业务一个串行队列。数据库锁/版本配合幂等唯一键，不靠进程内锁保证重启安全。
- 事件乱序按 captureOrdinal 和 revision 校正；迟到消息使相关未发回复过期。无法恢复顺序时人工处理，不自动拼接。
- “本系统幂等处理”不能写成“微信端严格 exactly-once”。GUI 端没有事务与官方消息确认，UNCERTAIN 是必须保留的状态。

## 7. Phase 0—10 实施计划

执行依赖：

```text
0 创建两个项目+能力验证 → 1 工程契约 → 2 监听去重 → 3 聚合语音
  → 4 AI 草稿 → 5 RAG → 6 Tool → 7 Guard/AUTO
  → 8 定时行情 → 9 OCR → 10 运维与交付
```

UIA 不可用时，Phase 0 只准提前执行 Phase 9 的“只读能力验证与 OCR 原型”，其消息与安全契约仍按 Phase 1—3 建立；不得跳过前置阶段直接 AUTO。若 UIA、OCR 均不可靠，转“人工粘贴 → AI 草稿”路线，并明确 RPA 实施阻塞，不假称完成。

所有阶段均需更新 `docs/phases/phase-NN.md`：范围、前置证据、任务状态、变更目录、接口/迁移、测试命令与实际结果、未验项、回退、下一阶段入口。每阶段按小任务提交可审阅 diff，避免一次生成整套生产系统。

### Phase 0：创建两个新项目与本机可行性验证（第一阶段）

**目标**：在指定 F: 路径创建独立后端 wechat-ai 与前端 wechat-ai-web，完成最小启动和联通；验证首选 RPA 底座的账号、测试私聊、文本、方向、监听、语音和输入读取能力。真实测试发送只在明确授权后进行。

**前置条件**：F: 盘及两个父目录存在或可安全创建，JDK/Maven Wrapper 所需运行环境、Node/npm、Python 可用；Windows 10/11 x64 交互桌面。项目初始化不依赖微信已登录，微信探测需人工登录测试账号和指定测试会话。没有发送授权时先完成创建与全部只读项，把发送项保留未验。

**具体任务**：

1. Codex 检查 `F:\ideaProject\wechat-ai`、`F:\TraeProject\wechat-ai-web` 是否存在及写入条件。均未创建时在各自父目录新建并分别初始化本地 Git；意外存在时先读文件和未提交修改，保留已有内容。不读取或改动 mc-ai 工程。
2. 初始化后端 Spring Boot Maven 工程：项目名/artifactId=wechat-ai，候选 groupId=com.wechat，包名=com.wechat.ai；固定可验证 JDK/Boot 稳定版本，创建 Wrapper、最小启动类、只返回 OFF 与应用名的受限 `/api/v1/admin/status`，开发 profile 使用合成状态。此时不连真实模型/业务库或实现客服模块。
3. 初始化前端 Vue 3 + TypeScript + Vite 工程：package name=wechat-ai-web，锁定 Node/npm/Vite 与依赖；创建首页显示项目名、有效 OFF 和后端连通状态；设置开发 `/api` 代理。生产构建可独立成功，地址可配置，响应不含聊天和身份数据。
4. 后端建 `agent/`、`docs/` 与需求基线，前端建独立 README/AGENTS.md/契约版本说明；记录两个路径、启动/构建命令和依赖。Agent 不混入 Maven/前端构建。
5. 核对上游 README、LICENSE、源码与安装发行名，固定 tag/commit 与 Python 依赖；在后端 `agent/.venv` 隔离安装。
6. 编写 probe：打印脱敏环境、微信版本、账号观察能力、窗口标题/资料可读性、当前输入读取能力、支持的监听/转写方法。
7. 打开测试会话并校验私聊身份，读取 recent snapshot；发送动作先检查目标、输入为空、固定文案及急停。不启动上游整套 AutoReply。
8. 人发送文本、两个相同文本、自己发消息、连续文本、语音、换会话、改备注；记录 raw snapshot 和方向差异，不处理真实客户。
9. 测试锁屏/解锁、缩放/窗口调整、微信失联、网络断开，验证暂停与恢复，不自动重新登录。
10. 4 小时只读/低频测试运行，采集缺失、重复与 UI 异常，记录可见会话数上限；不能通过高频发消息“压测平台”。
11. 输出 `GO_UIA / GO_OCR_DRAFT / NO_GO`，列每项能力 PASS/FAIL/UNVERIFIED。项目创建与 RPA 能力分开验收；身份不可验证或发送不可观察项阻止 AUTO。

**目录交付**：`F:\ideaProject\wechat-ai\pom.xml`、Wrapper、最小 `src/`、`agent/tools/probe.py`、`agent/tests/windows/test_probe_manual.md`、`docs/compatibility.md`、`docs/acceptance/phase-00-report.md`、脱敏快照；`F:\TraeProject\wechat-ai-web\package.json`、锁文件、最小 `src/`、Vite/代理配置、独立 README/AGENTS.md。

**API**：仅最小受限/开发合成 GET `/api/v1/admin/status`，返回 appName=wechat-ai、effectiveMode=OFF、schemaVersion；Phase 1 完成正式认证与状态 DTO。本地 CLI `python agent/tools/probe.py --read-only` 与受控 `--send-test`。不建设业务消息/回复/发送服务。

**数据模型**：BootstrapStatus、ProjectManifest、CapabilityReport、AccountObservation、ContactObservation、ChatSnapshot、InputSnapshot、ProbeResult；记录两工程依赖与 SDK commit，不需要业务数据库。

**验收**：两个项目位于指定绝对路径并各自可构建；后端启动、前端启动/构建、开发首页经 `/api` 访问最小状态成功；默认 OFF，无明文密钥；两仓库初始化不影响父目录/其他项目。RPA 验收另含窗口、账号、两测试会话可验证、IN/OUT、重复文本、授权测试发送、4 小时证据、语音状态和锁屏/身份冲突阻断。

**失败回退**：创建/构建失败保留已有内容并报告实际路径/工具阻塞，不删除项目重试、不换到 mc-ai；RPA 失败核实依赖/语言/DPI，UI 不可读进入 OCR 只读验证。不能用注入、注册表绕过策略或解密数据库修复。NO_GO 时两个已建工程保留并以 Fake/人工草稿继续独立工作，明确 RPA 未验/阻塞。

### Phase 1：工程骨架、契约与安全配置

**目标**：建立可运行的 Agent/后端/数据库骨架和 FakeAdapter，确定 API/模型与配置版本，所有真实发送功能默认关闭。

**前置条件**：Phase 0 两个新工程已创建并通过最小构建/连通测试，RPA 路线已有结论；受限路线可使用 FakeAdapter 继续。外部模型密钥缺失不阻止 FakeModel 骨架。

**具体任务**：

1. 完善已创建的 wechat-ai 与 wechat-ai-web，不重新初始化、不改 mc-ai；加入兼容的 Spring AI BOM、Python 包与锁文件、前端 API client 和契约版本验证。
2. 补齐第 3 节目录及两个仓库最小 AGENTS.md；记录 ADR、dependency-lock、.gitignore、无密钥配置示例。
3. 编写 OpenAPI 和事件/命令 JSON Schema，生成或验证 Java/Python DTO，保证字段与枚举一致。
4. 添加 Flyway 基础表 agent/account/runtime_policy/audit 与 Agent SQLite 迁移。
5. 实现 register/heartbeat/status/mode（只允许 OFF/DRAFT），认证、版本检查、错误结构与配置校验。
6. FakeAdapter/FakeModel 支持合成消息、身份冲突和异常；提供 dev-up/verify 脚本，仅启用仿真模式。
7. 给 /health 与管理指标区分 liveness/readiness；后台不可用不使 Agent 连续重启并误发。

**目录交付**：`Java/gateway/`、`agent/src/wechat_agent/adapters/{base,fake}.py`、`agent/src/wechat_agent/transport/`、`docs/contracts/`、`deploy/compose.yml`、`scripts/dev-up.ps1`、`docs/adr/001-stack.md`。

**API**：5.2 register/heartbeat，5.3 status/mode；未实现业务接口返回明确未启用错误，不能用假成功占位。

**数据模型**：AgentSession、CapabilityReport、RuntimePolicy、ConfigVersion、ErrorEnvelope；数据库 migrations V001；没有明文 token/API key 表字段。

**验收**：干净环境可运行 FakeAdapter 和健康检查；无 token 被拒绝；跨 agent 越权被拒绝；非法 enum/旧 schema 拒绝；断后台只缓存/暂停；生产配置默认 OFF，测试数据不触发真微信。

**失败回退**：两个新工程回到 Phase 0 的最小 OFF 启动状态；依赖冲突只在 wechat-ai 内选兼容 BOM，不改其他项目；删除数据库前先备份，不为恢复测试破坏业务库。

### Phase 2：白名单监听、方向识别与可靠去重

**目标**：把正确联系人发来的新消息可靠落库，解决重复快照/网络重试/重启，不接入 LLM 自动回复。

**前置条件**：Phase 1 合同与存储通过；目标 Adapter 的 read_snapshot/身份能力已验证。

**具体任务**：

1. 实现人工绑定页/API，建立 contactKey 与 accountKey、私聊证据、bindingVersion；配置仅两测试会话。
2. 实现唯一 UiActor、桌面互斥，Listener 观察已绑定会话；禁止底座 AutoReply。
3. 实现 baseline、快照序列对齐、方向分类、logicalMessageId、captureOrdinal、持久游标。
4. 捕获先提交 SQLite，再创建 event_outbox；后端 events:batch 原子去重和 message 入库。
5. 实现网络退避重试、有界队列、部分 ACK、持久重放、gap 和 unobservable 上报。
6. OUT 消息关联 journal；未识别 OUT 发 human-out 事件，暂不调用 AI。
7. 回放相同文本、历史滚动、重启、新未读被人工清除、语音显示变化等夹具。

**目录交付**：`agent/src/wechat_agent/receive/{listener,aligner,cursor}.py`、`agent/src/wechat_agent/storage/`、`Java/message/`、`Java/identity/`、`test-fixtures/messages/`、`docs/acceptance/phase-02-report.md`。

**API**：configuration、events:batch、contacts/bindings、contacts 更新、conversation/messages。

**数据模型**：ContactBinding、Conversation、Message、MessageRevision、EventInbox、LocalCursor、EventOutbox；unique 键按第 6 节。

**验收**：同一 event 重放 10 次只落一份；两条同内容 IN 保存为两条；OUT/UNKNOWN 不触发问答；重启不回复 baseline 历史；20 分钟断网补交不丢已捕获事件；名称冲突/账号变化阻断；捕获范围与 gap 明确。

**失败回退**：仅保存待审原始观察，不继续自动业务处理；对齐失败标 gap 并人工建立新 baseline；仍可用 FakeAdapter 继续开发后台，不把仿真通过写成真人通过。

### Phase 3：消息标准化、聚合、语音与接管

**目标**：把连续文本/语音统一成持久化 batch，保留顺序与不完整状态，为一次问答提供完整输入。

**前置条件**：Phase 2 的消息身份、方向与去重通过；语音 UI 能力已测或声明不支持。

**具体任务**：

1. Normalizer 标准化 Unicode 与空白，保留原始类型、转写来源、时间质量；不删掉数字/单位或擅改语义。
2. 用 conversationKey 实现 quiet/hard/voice deadline，时间与状态持久化，不依赖内存定时器。
3. 实现微信自动转写读取/正常菜单转写，精准绑定原语音 ref；按 revision 更新原消息。
4. 未转写保留位置，超时 PARTIAL_REVIEW，迟到转写使旧草稿过期；不用音频缓存解密。
5. 新 IN 推进会话版本；接管 API 与 OUT 人工操作推进取消事件。
6. 重启扫描未完成 batch，按确定规则恢复/过期；撤回/空文本/超长消息转人工。
7. 创建 fake clock 测试，避免测试实际等待几十秒；真实语音另做人工夹具验收。

**目录交付**：`Java/aggregate/`、`Java/message/Normalizer`、`agent/src/wechat_agent/receive/voice.py`、`Java/admin/Takeover`、`test-fixtures/messages/mixed-voice.json`。

**API**：MESSAGE_UPDATED、HUMAN_OUT_OBSERVED；takeover；可选内部只读 batch 查询供验收，不开放任意执行聚合接口。

**数据模型**：AggregateBatch、BatchMember、TranscriptResult、ConversationRevision、TakeoverState；batch 状态 OPEN/WAITING_VOICE/READY/PARTIAL_REVIEW/CANCELLED。

**验收**：0/2/4 秒三条文本仅一 batch，8 秒静默结束；连续消息 15 秒封口，语音延长等待最多 45 秒；两个同长度语音不合并成一条；文字+语音顺序正确；转写重复更新不新建消息；接管取消待处理，重启不重复封批。

**失败回退**：禁用语音自动处理，语音整批转人工；聚合状态异常停止该会话，不按单消息连发；恢复前核对持久成员与版本。

### Phase 4：Spring AI 与完整 DRAFT 闭环

**目标**：客户消息产生草稿，运营人员看到问题、来源、失败原因，能编辑/丢弃/接管。先把 AI 调用稳定下来。

**前置条件**：Phase 3 通过；模型 provider 的真实配置授权可用，或先 FakeModel。尚无 RAG/Tool 的公司事实问题必须人工。

**具体任务**：

1. 实现 ReplyService、ChatClient adapter、IntentRouter 与结构化 ReplyCandidate；限定提示词与数据边界。
2. 基础 ReplyPolicy：只允许 DRAFT，拒绝无证据公司事实、行情和项目数据；small talk 可生成不含事实承诺的草稿。
3. 分离 ConversationMessage 与模型记忆，按会话隔离；设置 token/耗时/费用预算，超时进入人工。
4. 模型调用完成再比较 conversationRevision；新消息来了旧结果 STALE，不能继续填入。
5. 实现管理台状态、消息、草稿、编辑、丢弃、接管与模式视图，展示有效模式与原因。
6. 默认草稿仅在管理台；本阶段不启用真实 FILL_ONLY/SEND_ONCE，界面显示功能未开放；完整 Guard 与填入/发送在 Phase 7 一并启用。
7. FakeModel 测 schema 错误、超时、空响应、超长、注入；真实模型用合成问题核查配置。

**目录交付**：`Java/ai/`、`Java/policy/`、`src/main/resources/prompts/`、`wechat-ai-web/src/views/{Status,Conversations,Drafts}.vue`、FakeAdapter 中的拒绝发送断言。

**API**：replies 列表/编辑/丢弃；approve 的 FILL_ONLY/SEND_ONCE 返回 FEATURE_NOT_ENABLED；Agent commands 返回空，不返回真实 GUI 指令。

**数据模型**：ReplyCandidate、Reply、ReplyRevision、DraftStatus、ModelInvocation、基础 PolicyDecision；记录模型/provider/promptVersion/token/latency。

**验收**：30 个合成场景有可读草稿或明确人工状态；provider 超时无自动重试 UI；编辑推进 revision；新消息作废草稿；调用任何填入/发送入口均返回未启用，零 UI 写入/发送动作。

**失败回退**：切 OFF，保留人工消息视图；切 FakeModel 验证后端，不丢事件；AI 不可用时生成工单而非自动发“系统出错”刷屏。

### Phase 5：知识库 RAG、来源与权限

**目标**：基于授权资料生成能追溯来源的 FAQ 草稿；实现资料更新、删除与客户/项目隔离。

**前置条件**：Phase 4 草稿闭环；授权样本文档、embedding provider、pgvector 安装验证完成。

**具体任务**：

1. 实现文档上传/格式大小校验/任务状态，按真实格式抽取；损坏或扫描文件给出失败原因。
2. 文档版本/hash 去重，分块与 embedding 维度锁定；索引重建不影响旧可用版本。
3. 强制权限过滤检索，结果再检验权限、有效期与版本；不让模型覆盖过滤条件。
4. 给 ReplyCandidate 绑定 EvidenceRef，校验引用存在；空召回、冲突/过期均 DRAFT/HUMAN_REQUIRED。
5. 删除/撤权失效向量、缓存、引用草稿与未提交命令；审计记录操作者和范围。
6. 建立 50 道黄金问题：30 可答、10 无答案/冲突/过期、10 跨客户/提示注入；按人工标注结果评估。

**目录交付**：`Java/rag/{ingest,retrieve,evidence,acl}/`、`wechat-ai-web/src/views/Knowledge.vue`、`test-fixtures/rag/`、`docs/acceptance/rag-evaluation.md`。

**API**：knowledge/documents 上传、jobs 查询、DELETE 撤权；回复返回 documentId/chunkId/version，不暴露内部文件路径。

**数据模型**：KnowledgeDocument、KnowledgeChunk、ImportJob、EvidenceRef、AccessScope、EmbeddingProfile；迁移 pgvector 向量与元数据索引。

**验收**：30 道可答问题至少 27 道正确且引用有效；无答案题不得编造；10 道越权/注入测试零泄露；同文件重复导入不倍增；撤权后新检索不可见且旧未发草稿失效；数字/条款需要人工逐题核对。

**失败回退**：关闭 RAG、回到 DRAFT+人工；保留前一索引版本；embedding 维度错误新建索引，不破坏性重置生产表。

### Phase 6：MarketTool、ProjectTool 与 RoutePlan

**目标**：回答真实数据问题，Tool 有输入 schema、授权、数据时效与确定性计算；fixture 与真实数据明确隔离。

**前置条件**：Phase 5 权限通过；项目客户绑定已人工核实；行情源接口与使用授权已确认，缺失时仅 fixture 验收开发项。

**具体任务**：

1. 定义 RoutePlan/ToolInput/ToolResult schema，受控意图 → 所需工具，最大 3 次调用、超时和预算。
2. MarketDataProvider 抽象，先 FixtureProvider 再接授权真实 API；后端校验域名/凭证/参数，不任意爬取。
3. ProjectTool 从可信上下文解析 allowedProjects，仅返回客户可见字段；拒绝模型伪造 projectId 越权。
4. 单位/税费/地区/规格可比性校验与 BigDecimal deltaCost；保留输入快照、时间与舍入规则。
5. 输出 EvidenceRef 和 asOf；过期或 fixture 标记进入 DRAFT，不写“今日实时”。
6. 管理台只读诊断与来源显示；超时、权限拒绝、缺参数转人工/澄清，不让 AI 填假的数字。
7. 建立标准行情、跨规格、跨客户、零采购量、负价差、空来源、数据过期测试。

**目录交付**：`Java/tool/{market,project,cost,executor}/`、`Java/ai/route/`、`test-fixtures/tools/`、`docs/adr/market-provider.md`。

**API**：tools/diagnostics；业务 Tool 不向 Agent 公开 API，不暴露给未认证客户；Reply 里增加结构化事实/证据。

**数据模型**：RoutePlan、MarketQuote、ProjectSummary、CostImpact、ToolCall、MarketSnapshot、ProjectSnapshot、TrustedCustomerContext。

**验收**：BigDecimal 结果与人工算例一致；货币/单位不匹配不计算；无授权项目返回拒绝；缺市场条件生成澄清草稿；Tool 超时零虚构；fixture 永不通过 AUTO；真实数据至少 10 个查询比对源 API，未配置真实源记录未验。

**失败回退**：禁用故障 Tool，保留知识问答与人工草稿；缓存数据必须标时效且不自动作“当前”答复；不得用 LLM 猜行情兜底。

### Phase 7：ReplyPolicy、SendGuard、人工单次发送与 AUTO

**目标**：完成唯一安全发送入口及本地急停；先验证人工 SEND_ONCE，再对指定测试联系人/意图开 AUTO。

**前置条件**：Phase 0—6 P0 全部通过；身份/输入/回执可验证；接管与新消息使旧草稿失效；受控测试发送已获授权。

**具体任务**：

1. 完整实现 4.7 的确定性策略，生成 reasonCodes；为 AUTO 配置明确意图允许列表与业务时段。
2. 后端 approval/command/outbox 与 claim/authorize-fill/prepared/commit/receipt 状态机，原子版本检查、短期 token、失效/取消；FILL_DRAFT 在 FILLED 结束，不进入 commit。
3. Agent Guard/journal/executor；发送前持久化 COMMIT_INTENT，按 UIA 观察增量回执，不按“输入框清空”确认。
4. 连接本地急停热键、管理台急停、OFF、锁屏、账号变化、人工 OUT 与输入变化；UI actor 禁第二发送进程。
5. 新入站、联系人更名、mode/binding/policy 版本变化撤销旧命令，填入后变更安全清理/接管。
6. 网络丢包/崩溃各边界注入；重复 command/commit/receipt 仅返回状态，UNCERTAIN 人工 reconcile。
7. FakeAdapter 完成全部矩阵后，在测试会话验证 SEND_ONCE，再单个联系人 FAQ/真实标准行情 AUTO；其他保持 DRAFT。
8. 管理台展示 PREPARED/UNCERTAIN 与证据，禁止“失败一键自动重发”。

**目录交付**：`Java/{policy,send}/`、`agent/src/wechat_agent/send/{guard,journal,executor}.py`、`agent/src/wechat_agent/ui/actor.py`、`wechat-ai-web/src/views/Commands.vue`、`docs/acceptance/send-safety.md`。

**API**：所有发送 Agent API、SEND_ONCE、runtime/mode AUTO、emergency-stop、commands/reconcile。

**数据模型**：ReplyApproval、SendCommand、CommitAuthorization、SendJournal、SendReceipt、GuardResult、RateBudget；每个字段与终态规则在 OpenAPI/schema 固定。

**验收**：第 8 节发送矩阵全部通过；FakeAdapter 1000 条混合故障命令零错发/重复 UI 发送；真实 20 次受控发送到两测试会话正确；锁屏/输入非空/重名/接管/新消息/过期/断后端全阻断；按键前后崩溃均不盲重发；本地急停标志响应目标 ≤1 秒，远程急停展示确认延迟并说明竞态边界。

**失败回退**：立即 OFF，保留完整 journal 与审计，人工核对 UNCERTAIN；只保留管理台草稿。任何错发、重复或身份失效不得以调限流参数继续 AUTO，修复并复跑受影响矩阵后才恢复。

### Phase 8：定时行情、订阅和任务恢复

**目标**：固定客户按授权排期接收有效行情，每个计划触发只创建一次候选命令，沿用全部安全检查。

**前置条件**：Phase 7 通过；真实行情源、订阅同意与业务日历已配置。无真实源只允许 fixture 草稿演示。

**具体任务**：

1. 实现 Subscription 与排期校验，必填时区、市场查询条件、同意记录与停止时间。
2. materialize scheduledFor、唯一键、数据库锁领取；使用 fake clock 检查时区和工作日，不用外部 API 压测。
3. 创建 market snapshot、reply、schedule_run，Policy 加入订阅/过期/静默期规则；无直接 sender 调用。
4. misfire=SKIP，重启后标过期；取消订阅撤销未提交 command。
5. 同步入站优先与人工接管，定时回复不能插入未完成客户问答；每人独立限额。
6. 管理台查看/暂停任务、排期预览和历史；失败是运营告警，不向客户刷失败通知。

**目录交付**：`Java/schedule/`、`wechat-ai-web/src/views/Subscriptions.vue`、`test-fixtures/tools/market-calendar.json`、`docs/operations/scheduling.md`。

**API**：subscriptions 新增/更新、schedule-runs 查询；调试手动运行必须专用权限且仍通过 Policy/Guard，默认只生成草稿。

**数据模型**：Subscription、ScheduleRun、CalendarVersion、ScheduledReply；unique(subscriptionId,scheduledFor)、market_snapshot 可复用但收件人命令不可共用。

**验收**：重复触发/两 worker/重启只建一次 run；09:00 上海时刻对应 UTC 正确；错过 10 分钟不补发；取消、OFF、DRAFT、接管、假行情和过期数据不 AUTO；一联系人失败不影响其他人的任务状态；两测试订阅真实时刻验一次。

**失败回退**：暂停所有订阅并取消未提交指令，保留手动查询草稿；不能绕过 Guard 改用群发工具补发。重启先预览未来排期，不自动清空任务表。

### Phase 9：OCR fallback 与能力降级

**目标**：UIA 消息读取不可靠时，提供可评估的 OCR 只读/草稿能力，并保持相同事件、去重与权限契约。

**前置条件**：Phase 1—3 契约/对齐器可用；已明确 UIA 哪些能力仍可用；目标 Windows/DPI 有已授权脱敏截图。Phase 0 可先做本阶段只读原型。

**具体任务**：

1. OCR 依赖独立安装与锁版本，验证中文 CPU 推理；只截图微信授权区域。
2. 建立窗口锚点/ROI 配置与 DPI 校准；移动、缩放、遮挡立即暂停，不盲操作。
3. OCR 输出 bbox/text/score/frameHash，连续稳定帧与气泡方向/上下文对齐，保留重复文本出现次序。
4. 复用事件 schema、logicalMessageId、cursor 与 backend，不建立另一条直接 LLM→sender 流程。
5. 能力变更取消所有旧指令并切 DRAFT；纯 OCR 无独立身份/输入核对时禁止系统填入/发送。
6. 低分、金额/日期歧义、重名、转写不可定位统一人工；原图默认不保存，测试图使用合成/脱敏。
7. 评估 100 张目标 DPI 截图及 UIA→OCR→UIA 切换，报告适用范围与未解决布局。

**目录交付**：`agent/src/wechat_agent/adapters/ocr.py`、`agent/src/wechat_agent/ocr/{engine,roi,parser}.py`、`agent/tests/replay/ocr/`、`test-fixtures/ocr/`、`docs/acceptance/ocr-report.md`。

**API**：CAPABILITY_CHANGED、MESSAGE_OBSERVED/UPDATED.source=OCR、READ_GAP；OCR 使用同一后端，不新增绕过 Guard 的发送 API。

**数据模型**：OcrObservation、BoundingBox、RoiProfile、OcrConfidence、AlignmentResult、CapabilityVersion；OCR score 不转换成联系人置信度。

**验收**：受支持截图方向/联系人错误接受数为 0，所有歧义拒绝；100 图中 ≥95 图正确读取或安全拒绝且统计拒绝率；完整可用消息读取率目标 ≥90%，否则明确功能受限；窗口变化立即降级；切换不重复答复；OCR 标记的命令不能通过 AUTO。

**失败回退**：关闭 OCR，进入人工粘贴/草稿；记录失败样本和限制。不放宽身份门槛来提高识别率，不接入数据库解密或任何 Hook 底座。

### Phase 10：监控、部署、回归与完整交付

**目标**：在真实 Windows 交互桌面与后端环境稳定运行，具备故障告警、备份恢复、升级回滚和可审阅证据。

**前置条件**：Phase 0—9 报告齐全；必需能力真实验证；业务负责人确认数据授权、保留策略和准入客户/意图；所有未验项列出。

**具体任务**：

1. 实现指标/告警/审计搜索与队列滞留、gap、心跳、UNCERTAIN、限流、索引/Tool 故障检测。
2. 后端+PostgreSQL 可容器部署；Agent 必须登录用户交互桌面启动，设置“仅用户登录时运行”的计划任务，不作为 Session 0 GUI 服务。
3. 运行脚本检测配置、版本、桌面状态、依赖、数据库迁移和磁盘空间；所有恢复默认 OFF。
4. 做数据库/自有 SQLite/配置备份，恢复演练验证状态与 pending command；发送 journal 不可回退为未发送。
5. 打包带确切版本和哈希的发布件、依赖/版权清单；升级保留旧包，数据库用兼容迁移，先 DRAFT 验证。
6. 回归单元/契约/集成/E2E/真实 Windows 矩阵；做 DRAFT 24 小时、受控 AUTO 8 小时观察，统计延迟、去重、人工回退和 UI 失效。
7. 写 runbook、常见故障、急停/接管/UNCERTAIN 核对流程、升级/回滚/重新绑定步骤。
8. 交付 README、阶段报告、接口、schema、迁移、测试结果、依赖锁、业务配置与已知限制；确认无密钥/真实聊天进仓库。

**目录交付**：`Java/audit/`、`scripts/{verify,backup,restore,agent-start}.ps1`、`deploy/windows-task-template.xml`、`docs/operations/runbook.md`、`docs/acceptance/final-report.md`。

**API**：status/audits/reconcile；受认证 readiness/metrics；不对公网暴露未认证 Actuator 或 Agent 控制接口。

**数据模型**：AuditEvent、HealthSnapshot、MetricLabels、ReleaseManifest、BackupManifest；记录 UTC 时间及 UI/模型/策略/依赖版本。

**验收**：第 8 节全部发布项通过；DRAFT 24h、AUTO 8h 实际报告；0 错发/重复/越权；恢复演练可重建业务状态且无旧指令自动发送；账号/客户端变更进入 OFF；运营人员能按 runbook 完成急停和 UNCERTAIN 核对。

**失败回退**：保留上一发布包和兼容数据库；故障环境 OFF/人工服务，关闭订阅。若时间观察或真人测试未完成，交付标“待验收”，不能宣布生产就绪。

## 8. 测试与最终验收

### 8.1 测试分层

| 层 | 验证内容 | 环境 | 产出 |
|---|---|---|---|
| 单元 | 快照对齐、聚合时间、规则、单位/金额计算、状态转换 | pytest/JUnit + fake clock | 可重跑报告 |
| 契约 | Java/Python JSON 一致、必填/枚举/版本/幂等 | schema + HTTP mock | 合同兼容报告 |
| 集成 | PostgreSQL/Flyway/事务 inbox/outbox/pgvector/授权 | 隔离 Testcontainers/测试库 | 迁移、并发与回滚证据 |
| 回放 | 重复快照/乱序/重启/转写/OCR | 合成/脱敏夹具 | 可核对 logical ID 与 batch |
| 故障注入 | HTTP 丢包、进程崩溃、磁盘满、重复指令、commit 竞态 | FakeAdapter | 不重复发送的动作记录 |
| 管理台 E2E | 审阅/编辑/批准/接管/OFF/订阅取消/CSRF | Playwright + fake API | UI 操作与审计关联 |
| 模型评估 | 来源正确、无答案拒答、权限、注入、数字一致 | 黄金集 + 指定模型 | 人工标注与统计 |
| 真实桌面 | 账号、联系人、UI/语音、输入、发送、锁屏 | Windows 测试账号 | 实际耗时与脱敏证据 |

前六层可由 Codex 自动执行；真实桌面能力依赖可用工具与正常用户会话。测试环境没有桌面权限时，Codex 完成脚本与夹具，列清人工步骤，不冒充已经实际点击微信。

### 8.2 关键场景矩阵

| ID | 输入/故障 | 期望 |
|---|---|---|
| T01 | 单条新 IN 文本 | 一份消息、batch、有效草稿 |
| T02 | 同一快照观察 10 次 | 不重复创建逻辑消息 |
| T03 | 两条相同文本、同一分钟 | 两条消息、保持次序 |
| T04 | OUT 系统回声/人工 OUT | 不触发 AI；人工 OUT 接管 |
| T05 | UNKNOWN 方向、群聊、非白名单 | 不进入自动问答 |
| T06 | 新消息未读被人工清掉 | 可读快照仍能识别，不能只靠红点 |
| T07 | 首次启动与滚动旧历史 | 建立 baseline，不答历史 |
| T08 | 断网后重传/部分 ACK/后端提交后 ACK 丢失 | 幂等入库，本地仅删除已确认项 |
| T09 | 重启/UI RuntimeId 改变/锚点丢失 | 保留游标或标 gap，禁止猜新消息 |
| T10 | 文本 0s/2s/4s 到达 | 同一 batch，静默期后就绪 |
| T11 | 一直来消息/超过条数长度 | 最长窗口封批，超限 DRAFT/人工 |
| T12 | 连续语音与文字混合 | 同 batch 按原序位，转写更新原 ID |
| T13 | 转写失败/晚于 deadline/重复转写 | PARTIAL_REVIEW；旧草稿 STALE，不自动修正连发 |
| T14 | AI 生成中出现新 IN | 旧版本不能批准/发送 |
| T15 | 接管后收到消息或定时任务 | 无 AI 新任务/自动发送，旧命令撤销 |
| T16 | 文档无答案/过期/冲突 | 人工草稿，不虚构公司事实 |
| T17 | 客户跨项目、文档/Tool 提示注入 | 服务端拒绝，零未授权数据 |
| T18 | Tool 超时/缺地区规格/单位不同 | 无假数字、明确澄清/人工 |
| T19 | fixture 行情/过期行情 | 不通过 AUTO，不称实时 |
| T20 | 重名好友/好友与群同名/搜索为空 | 不默认第一项，零 UI 写入 |
| T21 | 当前有人工草稿/输入法或弹窗干扰 | 不覆盖，接管/阻断 |
| T22 | 填入后被人工修改/切换聊天 | 输入 hash/身份不匹配，禁止发送，不删用户新内容 |
| T23 | 编辑已批准草稿/联系人更名/策略变化 | 旧 revision/token/命令全部失效 |
| T24 | TTL 到期/新账号/锁屏/注销 | 不输入、不发送，OFF 或安全暂停 |
| T25 | 同一 command 多次领取/相同 commit 请求/重复回执 | UI 发送至多一次，返回既有状态 |
| T26 | commit 回复丢失/按键前崩溃 | 不重新授权盲发；持久 journal 决定 UNCERTAIN |
| T27 | 已按发送但回执丢失/按键后崩溃 | UNCERTAIN，人工核对；不自动重发 |
| T28 | 输入框清空但未见 OUT/见发送失败符号 | 不标 CONFIRMED，不自动再按一次 |
| T29 | 历史已有同内容 OUT | 必须看到新的尾部增量，历史不能充当回执 |
| T30 | SQLite 写失败/磁盘满 | COMMIT_INTENT 未持久化不发送 |
| T31 | 一桌面启动两个 Agent | 第二实例退出/只读，不抢 UI |
| T32 | 本地急停/远程 OFF 正好遇 commit | 记录竞态与实际动作；检查最终本地标志，不声称 GUI 原子撤销 |
| T33 | 定时触发重复/多 worker/服务重启 | 同订阅时刻仅一 run，不能双发 |
| T34 | misfire/静默期/取消订阅/无日历 | SKIP/暂停，不补发积压消息 |
| T35 | 定时行情与入站问答同时发生 | 入站优先，旧推送草稿/命令暂停或失效 |
| T36 | OCR 相同文字/左右气泡/遮挡/重名 | 正确对齐或安全拒绝，不 AUTO |
| T37 | UIA→OCR→UIA | 能力变更撤旧指令，不重复处理 |
| T38 | token 越权、跨 Agent、CSRF、恶意上传路径 | 401/403/校验拒绝；无敏感回显 |
| T39 | 撤权、删除文档、聊天保留期到期 | 数据/向量/缓存联动清理，未发引用失效 |
| T40 | 备份恢复到旧时点 | OFF；旧 command 不再发送，核对本地 journal 与审计 |

### 8.3 发布硬门槛

- Phase 0 的目标环境与真实发送能力证据完整，目标微信/账号/语言/DPI 与当前一致。
- T01—T40 全部执行：PASS、明确限定或发布阻断。阻断条件不能用“后续优化”豁免。
- 错发、重复发送、非白名单发送、接管中自动发送、跨客户泄露、UNCERTAIN 自动重发任一出现即禁止 AUTO。
- RAG/Tool 黄金集达到阶段标准，真实数据源有授权和时效定义；fixture 从实际 AUTO 链路禁用。
- 单位、金额与时间口径通过人工检查；证据来源不能仅依赖模型生成的引用文本。
- DRAFT 24 小时和受控 AUTO 8 小时完成；p95 草稿生成 ≤30 秒（选定正常网络/模型）或明确记录未达标及仍采用 DRAFT 的限制。
- 备份恢复、升级回滚、急停接管演练成功；没有明文密钥、真实客户夹具或未授权截图进仓库。
- 即使全部通过，AUTO 仍按联系人与意图显式启用，不能把现有白名单一键全部切 AUTO。

### 8.4 验收报告模板

```markdown
# Phase NN 验收报告
- Git commit / 发布版本：
- 环境：Windows、微信、Python、JDK、Boot、Spring AI、数据库、DPI、语言
- 模式与真实测试授权范围：
- 本阶段目标及需求编号：
- 前置阶段证据：
- 修改文件/模块：
- API/schema/迁移版本：
- 测试命令、实际开始/结束时间、退出码与结果：
- 测试用例：PASS / FAIL / UNVERIFIED / NOT_APPLICABLE（理由）
- 实测统计：捕获数、去重数、gap、批次数、草稿、UI 发送动作、UNCERTAIN、p95
- 脱敏证据路径与 hash：
- 未解决项与 AUTO 影响：
- 回退动作及已验证结果：
- 结论：通过 / 有限制通过 / 阻断
- 下一阶段可执行范围：
```

## 9. 部署、运行与回滚

### 9.1 部署形态

**开发**：后端在 `F:\ideaProject\wechat-ai`，前端在 `F:\TraeProject\wechat-ai-web` 分别运行，Agent 在后端 `agent/` 独立启动。Phase 0 不引入业务数据库；Phase 1 开始本地 PostgreSQL/pgvector，先 FakeAdapter 再测试微信。Docker 不可用时采用本地测试 PostgreSQL；不能让 Codex 为跑测试接入或清空生产数据库。

**试运行**：专用 Windows 登录桌面运行微信/Agent；后端可在同机或内网服务器，Agent 经 HTTPS 主动连后端；操作台受认证和网络限制。

**生产约束**：Agent 位于微信的用户交互会话。Windows 服务默认在 Session 0，不能把操作微信的 GUI Agent 作为普通后台服务部署；参见[Microsoft Interactive Services](https://learn.microsoft.com/en-us/windows/win32/services/interactive-services)。Java/数据库可以作为服务或容器，但 GUI Agent 用“仅当用户登录时运行”的计划任务或人工启动。

锁屏、注销、切用户、RDP 会话变化均视为 UI 能力失效。系统暂停并告警，不设计保持桌面解锁的规避措施；恢复后先 OFF/自检/DRAFT，不自动 AUTO。

### 9.2 配置样例

以下是本项目拟定配置，不是 pyweixin/Spring AI 的原生配置键。Phase 1 应实现校验与对应映射。

```yaml
runtime:
  startup_mode: OFF
  timezone: Asia/Shanghai
  takeover_auto_release: false
  fake_adapter: true                 # 开发默认；生产须显式关闭
  allow_live_send: false             # Phase 7/10 前禁止打开
agent:
  backend_url: https://backend.example.internal
  token_env: WECHAT_AGENT_TOKEN
  heartbeat_seconds: 10
  offline_send: false
  max_contacts: 10
  ui_actor_count: 1
  emergency_hotkey: Ctrl+Alt+Shift+F12 # 部署前验证不冲突
aggregation:
  quiet_seconds: 4
  max_window_seconds: 15
  voice_item_timeout_seconds: 30
  voice_batch_timeout_seconds: 45
  max_messages: 20
  max_chars: 4000
reply:
  max_chars: 800
  draft_ttl_seconds: 300
  model_timeout_seconds: 30
  auto_intents: [FAQ, MARKET_QUERY]
  voice_auto_enabled: false
send:
  command_ttl_seconds: 120
  lease_seconds: 30
  commit_token_seconds: 2
  min_conversation_interval_seconds: 30
  contact_hourly_limit: 10
  account_hourly_limit: 30
  retry_uncertain: false
ocr:
  enabled: false
  allow_auto: false
  stable_frames: 2
  min_text_score: 0.95               # 需用目标截图评估，不代表身份可信度
schedule:
  misfire_policy: SKIP
  run_ttl_seconds: 600
retention:
  chat_days: 30
  runtime_log_days: 30
  failure_screenshot_days: 7
  audit_days: 90
```

真实 token、模型 key、数据库密码通过环境或凭证存储注入；`example.internal` 为占位地址。模型/provider/embedding 与报价源的具体 Spring 配置由锁定依赖实现，不在本文虚构服务商参数。

### 9.3 从需求到首次运行

1. 当前两个项目尚未创建。将本文作为 Codex 可读附件/需求来源，发送第 10 节启动提示词，由 Codex 在第一阶段 Phase 0 创建 `F:\ideaProject\wechat-ai` 与 `F:\TraeProject\wechat-ai-web`，并将本文保存到后端根目录 `requirements.md`。
2. 后端与前端分别可启动、构建和提交；在 Codex 中打开后端作为主开发上下文，前端使用明确绝对路径或单独项目上下文。前端跨聊天工作时使用后端契约与阶段摘要，不靠共享单仓库假设。
3. Phase 0 先做最小后端/前端联通，再人工正常登录测试微信并核实测试联系人，Codex 完成 probe 和安全只读验证；此时不开发完整 AI/数据库业务。
4. Phase 1 创建构建/运行脚本后，使用其 README 中实际命令。示例标准入口约定如下，阶段代码不存在时不能当现成命令执行：

```powershell
# Phase 0 创建两个工程后，各自工作目录执行最小构建
Set-Location -LiteralPath 'F:\ideaProject\wechat-ai'
./mvnw.cmd -DskipTests package

Set-Location -LiteralPath 'F:\TraeProject\wechat-ai-web'
npm run build

# 后续后台脚本均在后端根执行，前端独立使用 npm run dev/build
Set-Location -LiteralPath 'F:\ideaProject\wechat-ai'

# 由 Phase 1 创建，默认只启 FakeAdapter 与测试后端
./scripts/dev-up.ps1 -Mode Fake

# 汇总后端/Python/契约检查；真实桌面测试显式独立开关
./scripts/verify.ps1 -Profile CI

# Phase 0 验证脚本
python ./agent/tools/probe.py --read-only

# Phase 10 创建；先自检，实际模式仍 OFF
./scripts/agent-start.ps1 -Mode OFF
```

5. Phase 2—4 在两测试会话完成 DRAFT；输入填入与真实发送在 Phase 7 通过 Guard 后启用。
6. Phase 5—6 导入授权资料并接真实源；资料或凭证缺失先开发 fixture，保持真实源验收为未完成。
7. Phase 7 先单次人工批准，后单联系人 AUTO；Phase 8 单订阅验证；Phase 9 验证降级；Phase 10 达成完整发布门槛。

### 9.4 监控与告警

| 指标/条件 | 动作 |
|---|---|
| Agent 30 秒无心跳 | 后端停止新发，管理台离线；Agent 离线不发 |
| account_changed / identity_ambiguous | 撤销命令，OFF/重新核实，不自动切账号 |
| send_uncertain_total 增加 | 立即运营告警，暂停该会话自动发送，人工 reconcile |
| send_guard_block_total | 按原因累计；身份/版本异常暂停 AUTO，不仅记日志 |
| ui_action_latency / 读取失败连续 3 次 | DEGRADED，停止自动动作，保留事件 |
| read_gap / last_observed_age | 展示缺口与未观察会话，禁止声称完整监听 |
| event_outbox_age >60 秒 / 磁盘空间不足 | 告警、暂停 AUTO，保护本地日志与消息 |
| draft_generation_p95 >30 秒 / model_error | 运营提示和草稿回退；不向客户连发失败通知 |
| tool_timeout / quote_stale | 阻止相关行情 AUTO，保留其他可用 FAQ 草稿 |
| document_index_error / acl_failure | 暂停相关知识范围与发送，立即核对权限 |
| schedule_misfire / subscription_cancel | 记录 SKIP/取消，不重放旧行情 |

指标用有限状态/错误码标签，避免 contactKey、聊天内容或 commandId 造成敏感泄露和高基数。详细关联放审计查询。告警目标由用户配置，本文不默认替用户发送邮件/微信/Slack。

### 9.5 故障处理 runbook

**发现错发、重复或异常账号状态**：本地急停/全局 OFF → 停订阅 → 保存 journal/审计 → 人工核对实际微信 → 修复与复跑相关矩阵 → DRAFT 验证 → 必要时按联系人重新开放 AUTO。系统无法自动撤回已触发的发送，不能把撤回当可靠补偿事务。

**UNCERTAIN**：不点自动重发 → 查看指定账号/联系人/发送时刻和 UI 尾部 → 记录人工结论与证据 → 已发送则 reconcile → 无法确认则继续人工 → 证实未发送且确需补发时创建新的人工单次命令。

**微信升级或 UI 不可见**：OFF → 记录新版本 → Phase 0 重新探测 → 适配器按版本配置 → 假数据与真实桌面回归 → DRAFT。不得把定位失败替换成未经校验的坐标点。

**后台/模型故障**：Agent 保留本地已捕获事件，暂停发送；后端恢复后幂等补交，过期批次进入人工审阅，不自动回答几个小时前的客户消息。

### 9.6 备份与恢复

- 备份 PostgreSQL、自有 Agent SQLite、配置版本、发布 manifest；模型密钥使用独立凭证备份，不混在数据库 dump。
- SQLite 采用数据库 backup API 或停写后的受控备份，不直接复制正在写入的单个 `.db` 而遗漏 WAL。
- 备份保存 UTC 时间、schema、发布版本、hash 和保留期。加密与 ACL，恢复仅在隔离环境先演练。
- 恢复前 OFF 并停止 UI actor；后端恢复后旧未完成发送命令统一进入需核对状态，本地 journal 是判断 GUI 副作用的重要证据。
- 后端恢复旧备份但 Agent journal 较新时，先导入/核对回执再决定状态；不得删除 journal 以“清理失败任务”。若 journal 丢失，待发旧命令一律禁止自动再执行。
- 候选 RPO 24 小时、RTO 2 小时按试运行配置验证；该指标针对业务数据恢复，不承诺微信 GUI 全历史补齐。
- 发布升级采用向后兼容迁移、保留旧包和依赖；不可逆迁移必须在隔离恢复演练后另行规划，不能用自动 down migration 删除生产业务数据。

## 10. Codex 工作规则与提示词

### 10.1 执行原则

Codex 是开发工具，运行时客户回复由 Spring AI 服务生成。项目不需要为实时微信消息启动 Codex，也不需要把 Codex 登录状态当模型 API 凭证。人工微信登录与业务授权无法靠代码自动替代。

按“读取当前阶段 → 实现小范围任务 → 测试 → 输出可审阅变更和证据 → 更新阶段记录”推进。需要业务事实时明确假设并使用 fixture，不能把猜测写进生产配置。遇到非阻断小选择自行采用可逆默认值；缺真实数据授权或桌面权限时继续独立编码与测试，同时明确真实验收未完成。

仓库根放简短 AGENTS.md；接口看 contracts，业务行为看 requirements，部署时看 runbook，避免每个小任务重复读全部文档。Codex 可读取项目指令文件，机制参见[OpenAI 的 AGENTS.md 文档](https://learn.chatgpt.com/docs/agent-configuration/agents-md)。

### 10.2 建议 AGENTS.md 内容

以下供 Phase 0 写入两个新仓库的相关范围，Phase 1 完善，不应直接修改用户全局指令。前端 AGENTS.md 额外指定后端契约版本、API 生成与前端构建命令，不把后端 Maven 命令当作前端检查。

```markdown
# Project instructions

- 根据 requirements.md 当前阶段和 docs/phases/phase-NN.md 实现；业务需求变更同步记录。
- 工程为新建独立 wechat-ai（F:\ideaProject\wechat-ai）与 wechat-ai-web（F:\TraeProject\wechat-ai-web）。
- mc-ai 属于其他项目，不读取或修改；目标目录意外存在时先检查文件和未提交改动，保留已有内容。
- 只使用正常微信 UI Automation/OCR；禁止 Hook、DLL 注入、逆向协议、微信数据库解密。
- 不实现以规避平台检测为目的的 HID/仿生操作/错字/随机无关动作。
- 默认 FakeAdapter/OFF；真实测试仅限已授权账号、联系人、固定文案和范围。
- 所有 GUI 操作进 UiActor；所有写输入/发送进 SendGuard；不直接调用上游 AutoReply。
- LLM 不能决定收件人、权限或任意 Tool；后台验证证据和项目权限。
- UNCERTAIN 不重发；命令/事件/回执幂等，发送前持久化 COMMIT_INTENT。
- 接口变化看 docs/contracts，数据库变化写迁移；不要重置生产库。
- 只写本任务必要测试，运行影响范围内检查；真实桌面未执行写 UNVERIFIED。
- 不提交 token、聊天原文、客户截图、运行数据库；夹具合成/脱敏。
- 完成阶段更新实际命令、测试结果、限制、回退与下一入口，给出审阅 diff。
```

### 10.3 项目启动提示词

```text
请以这份需求文档为基线，执行 Phase 0（第一阶段）：创建独立前后端项目并验证本机 RPA 能力。
后端项目名 wechat-ai，创建于 F:\ideaProject\wechat-ai；前端项目名 wechat-ai-web，创建于 F:\TraeProject\wechat-ai-web。mc-ai 是另一个项目，不读取/改动它，不复制其业务实现。
先检查F:盘/父目录、工具、目标目录与相关AGENTS.md。目录不存在则分别创建与初始化本地Git；存在则保留文件并检查未提交改动，不删除覆盖，不在父目录初始化Git或推远程。
后端建最小Spring Boot/Maven/Wrapper/JDK21候选工程，前端建Vue3/TypeScript/Vite/npm锁文件工程，固定官方兼容版本；最小首页通过/api代理读取后端OFF状态，各自启动/构建。
把本文保存到后端 requirements.md，Python RPA放后端agent目录独立依赖，前端保持独立项目。生成两仓库README/AGENTS.md与创建验收证据。
随后做只读本机可行性验证，固定上游 pywechat/pyweixin 版本，检查真实 API，不凭记忆编造方法。
默认 OFF/Fake；没有已明确授权的测试目标和固定文案时不发送微信。
完成 probe、环境与能力报告、脱敏夹具、兼容矩阵和 Phase 0 记录；4 小时真实运行未完成不能标通过。
禁止 Hook、注入、逆向协议、微信数据库解密、平台风控规避仿生设计。
请完成可独立执行的代码与测试，不停留在口头方案。真实桌面或授权缺失时记录未验项，并完成不依赖它的工作。
最终给出两个实际工程路径、修改文件、启动/构建/连通实际结果、GO_UIA/GO_OCR_DRAFT/NO_GO 与下一阶段入口；项目创建和RPA测试分开报告。
```

### 10.4 每阶段通用提示词模板

```text
请执行 requirements.md 的 Phase {N}：{阶段名称}。
后端根 F:\ideaProject\wechat-ai；前端根 F:\TraeProject\wechat-ai-web；独立仓库，主需求与阶段记录在后端。不要读取或修改mc-ai。
前置证据：docs/phases/phase-{NN-1}.md 和相关 acceptance 报告。
本阶段范围：{明确任务及目录}。
先检查现有实现；已完成部分只核验，不重复重构。前置失败时修复所需最小范围，记录原因。
按本阶段目标、API/schema、数据模型、验收、失败回退完成代码、迁移、测试和运行说明。
遵守 OFF/DRAFT/AUTO、白名单、UiActor、ReplyPolicy、SendGuard、消息/命令幂等与 UNCERTAIN 禁重发。
未取得真实桌面测试条件/授权/数据源时使用 FakeAdapter/fixture 完成可独立工作，真实验收保持 UNVERIFIED。
不生成后续阶段的未使用功能，不安装无关插件，不复制未经审查的上游自动发送流程。
更新 docs/phases/phase-{NN}.md；输出变更、测试证据、限制和回退；不得把假数据结果宣称生产验证。
```

以下模板已具体化阶段范围，可直接复制。执行“下一阶段”前应核对前置验收，而不是把阶段编号当已完成证据。

### 10.5 Phase 0 提示词

```text
执行本文 Phase 0（第一阶段）：先在F:\ideaProject\wechat-ai创建后端wechat-ai、在F:\TraeProject\wechat-ai-web创建前端wechat-ai-web，再验证本机 Windows + 微信 + 测试账号。
两个目录尚未创建；先检测盘符/父目录/工具，目标不存在再初始化，意外存在保留，不操作mc-ai或其他项目。
最小后端Spring Boot/Maven Wrapper和前端Vue3/TypeScript/Vite分别构建，页面经/api代理读取OFF状态；不接真实模型或业务库。保存后端requirements.md及两仓库README/AGENTS.md/锁文件。
首选 Hello-Mr-Crab/pywechat 的 pyweixin；核实发行名、commit、LICENSE、真实 Navigator/Messages/Monitor API，隔离安装。
完成只读 probe：窗口、账号、联系人资料、文本读取、IN/OUT、重复文本、输入框可读性、语音转写能力、锁屏/换会话暂停。
测试发送只在已授权测试会话和固定文案内，基础校验联系人、输入为空、急停和发送后观察；不启动 AutoReply。
输出 compatibility、能力矩阵、脱敏快照与4小时报告。未实际运行的项目标 UNVERIFIED。
UIA 不可用仅做 OCR 只读验证/人工草稿路线，不绕过限制。给出 GO_UIA/GO_OCR_DRAFT/NO_GO。
```

### 10.6 Phase 1 提示词

```text
执行 requirements.md Phase 1，完善Phase 0已创建的wechat-ai与wechat-ai-web，建立Agent/后端/数据库和 FakeAdapter 骨架，不重新初始化。
后台F:\ideaProject\wechat-ai，前端F:\TraeProject\wechat-ai-web，RPA在后台agent/；不改mc-ai。固定Python/JDK/Boot/Spring AI/数据库依赖，按官方兼容矩阵配置BOM，前端API按同版本OpenAPI生成并记录schema hash。
实现 OpenAPI 3.1、JSON Schema、DTO、register/heartbeat/status/mode、认证、错误码、版本与配置校验。
创建 Flyway/SQLite 基础迁移、FakeModel、无密钥示例、AGENTS.md、dev-up/verify 脚本。
默认 OFF/Fake，不实现真实微信发送。验证未认证/越权/非法 schema/断线与原工程构建。
输出 dependency-lock、ADR、Phase 1 记录、实际测试证据与回退。
```

### 10.7 Phase 2 提示词

```text
执行 requirements.md Phase 2，实现白名单私聊监听和可靠去重，不调用 LLM。
建立人工 ContactBinding/internal UUID/version，不能将昵称当唯一身份或默认搜索第一项。
实现单 UiActor、baseline、快照序列对齐、IN/OUT/UNKNOWN、logicalMessageId、captureOrdinal、SQLite 游标和 event outbox。
实现 events:batch 后端 inbox 幂等、消息入库、部分 ACK、重启/断线补交、gap 与 unobservable。
测试同消息十次重放、两条同文本、历史滚动、RuntimeId 改变、OUT 回声、账号变化和断网补交。
任何方向或身份歧义仅待人工。记录真实读取范围与未验项，提交 Phase 2 报告。
```

### 10.8 Phase 3 提示词

```text
执行 requirements.md Phase 3，实现 Normalizer、持久 Aggregator、语音转写与人工接管。
同会话4秒静默/15秒最长聚合、20条/4000字限制，用 fake clock 测时间边界。
语音先占序位、同logicalMessageId更新revision；正常微信 UI 转写，单条30秒/整批45秒，失败 PARTIAL_REVIEW。
新IN推进会话版本，迟到转写作废旧草稿，OUT人工消息/接管取消待处理。重启从持久状态恢复。
禁止抓微信音频缓存、解密数据库或用不匹配语音位置的文本兜底。
测试文字+连续语音、重复转写、晚转写、重启、超限、接管与会话隔离，更新 Phase 3 证据。
```

### 10.9 Phase 4 提示词

```text
执行 requirements.md Phase 4，实现 Spring AI ReplyService 与 DRAFT 管理台闭环。
实现受控 IntentRouter、结构化 ReplyCandidate、超时/token预算、按会话记忆隔离与基础 ReplyPolicy。
公司事实/行情/项目没有证据时转人工，模型结果完成时比较 conversationRevision，旧结果标 STALE。
管理台显示原问题、草稿、理由、模型状态；支持编辑/丢弃/接管，默认只保存在操作台。
本阶段不启用真实发送/填入；FILL_ONLY/SEND_ONCE 按功能未启用处理，完整 Guard 在 Phase 7 开放。
用 FakeModel 测超时、坏JSON、空/超长输出、注入、新消息与编辑过期，再用授权真实模型合成问题联调。
更新 Phase 4 报告，不把模型自报置信度作为自动授权。
```

### 10.10 Phase 5 提示词

```text
执行 requirements.md Phase 5，实现文档导入、pgvector RAG、来源与权限。
支持授权MD/TXT/PDF/DOCX抽取，版本/hash去重、固定embedding维度、异步索引状态。
检索前强制客户/项目权限与有效期，结果后再校验，模型不能覆盖过滤条件。
回复保存documentId/chunkId/version/EvidenceRef；无答案、冲突、过期转草稿/人工。
删除/撤权联动向量、缓存、未发回复。使用50题黄金集测正确率、引用、越权与提示注入。
先保留 DRAFT，输出RAG评估、迁移、导入说明、限制与 Phase 5 报告。
```

### 10.11 Phase 6 提示词

```text
执行 requirements.md Phase 6，实现 MarketTool、ProjectTool、CostImpact 与受控 RoutePlan。
先 FixtureProvider，真实行情源未提供授权就记录未验，不自行挑未知接口爬取。
Tool输入schema、5秒单调用/15秒总预算/最多3次，授权来自可信contactKey上下文，不相信模型projectId权限。
行情带品类地区规格/单位币种税运费口径/asOf/source/有效期；项目只返回授权字段。
用BigDecimal计算可比价格×剩余采购量影响，记录舍入与输入快照；单位不符不算。
fixture/过期/缺条件/Tool失败不通过AUTO、不编数字。完成权限、口径、金额和真实源比对测试，更新 Phase 6。
```

### 10.12 Phase 7 提示词

```text
执行 requirements.md Phase 7，完成 ReplyPolicy、SendGuard、FILL_ONLY、SEND_ONCE 与 AUTO。
唯一UiActor+桌面互斥，后端approval/command/outbox/claim/authorize-fill/prepared/commit/receipt状态机，版本/hash/TTL/session校验；FILL_DRAFT只到FILLED后接管。
Guard核实账号和精确私聊身份，保护原输入，填入后读回，在线一次commit授权，发送前持久化COMMIT_INTENT，最后本地复核。
发送观察必须是新的目标OUT增量；按键后不确定为UNCERTAIN，禁止自动重发；重复命令/commit/receipt幂等。
OFF、急停、锁屏、接管、新IN、编辑、账号/版本变化撤旧授权；人工批准仅当前revision一次，不绕过OFF。
先跑FakeAdapter的T20—T32及1000条故障矩阵，再在已授权两测试会话验证人工单次与20次受控发送。
通过前所有真实AUTO禁用；通过后仅单测试联系人FAQ/标准真实行情开放。记录GUI竞态边界和 Phase 7 报告。
```

### 10.13 Phase 8 提示词

```text
执行 requirements.md Phase 8，实现订阅与定时行情，所有推送复用ReplyPolicy/SendGuard。
Subscription记录contactKey、查询条件、同意、时区、业务日历和取消状态；无日历/真实数据不AUTO。
数据库materialize scheduledFor，用unique(subscriptionId,scheduledFor)防重复，多worker/重启幂等。
misfire=SKIP、默认10分钟有效，OFF/DRAFT/接管/静默期/过期/取消不自动发，不补积压日报。
入站问答优先，每个收件人独立command；管理台显示排期预览与run状态。
用fake clock验上海时区、取消竞态、两worker、重启和数据过期，真实两测试订阅验一次，更新 Phase 8。
```

### 10.14 Phase 9 提示词

```text
执行 requirements.md Phase 9，实现可选 PaddleOCR 读取降级，复用同一消息/去重/后端契约。
仅截图授权微信区域，ROI/DPI/窗口锚点校准，两稳定帧、bbox/方向/顺序/上下文对齐，保留相同文字重复出现。
能力变更取消旧命令并进入DRAFT；纯OCR不能核实身份/输入时只管理台草稿，禁止AUTO和自动定时发送。
低分、金额日期歧义、重名、遮挡、窗口移动暂停/人工，不放宽Guard、不接任何Hook或微信数据库读取。
用100张合成/脱敏目标截图评估方向/身份错误接受为0、正确读取/安全拒绝和拒绝率，测试UIA↔OCR无重复。
输出安装/校准、精度范围、限制、失败回退和 Phase 9 报告。
```

### 10.15 Phase 10 提示词

```text
执行 requirements.md Phase 10，完成监控、部署、备份恢复、回归、运行文档与交付。
后端可服务/容器，微信Agent在用户交互桌面运行，计划任务仅用户登录时，不部署Session0 GUI服务。
实现心跳/队列/gap/UNCERTAIN/Guard/模型Tool/任务指标与运营告警、受认证status/metrics/audits。
启动升级恢复默认OFF；备份PostgreSQL/自有SQLite/配置manifest，恢复旧备份不重发旧command，先核对journal。
执行T01—T40、依赖与权限检查、DRAFT24小时/AUTO8小时真实观察；未完成真实测试明确UNVERIFIED。
整理runbook、急停/接管/reconcile、升级回滚、依赖锁/版权、接口/schema/迁移/测试报告/已知限制。
最终按发布硬门槛判定生产就绪或待验，不能因代码编译通过宣称全项目验收通过。
```

### 10.16 定位失败与恢复提示词

```text
当前 Phase {N} 失败，错误/日志如下：{脱敏信息}。
先读取该阶段记录和相关代码，复现最小失败并区分上游不支持、UI变化、契约、并发或业务配置问题。
保持OFF/DRAFT，保留消息与发送journal；不清生产库、不盲重试UNCERTAIN、不加入Hook/注入/逆向/规避检测方案。
修复必要最小范围，补一项能证明行为的回归测试，重跑受影响检查，更新阶段报告与限制。
如依赖真实桌面/账号/源API无法验证，完成仿真可验证工作，给出具体人工验证步骤及明确未验项。
```

### 10.17 每次 Codex 交付的最小内容

1. 本次实际完成的目标、阶段与需求编号。
2. 可审阅 diff、接口/schema/迁移变化、运行入口。
3. 已执行检查及实际结果，真实/仿真明确区分。
4. 未验项、风险边界、失败回退，当前有效模式。
5. 更新后的阶段记录和下一阶段入口。

## 11. 交付清单与待确认项

### 11.1 完整交付清单

- [ ] 第一阶段创建 F:\ideaProject\wechat-ai 与 F:\TraeProject\wechat-ai-web，分别构建/运行/联通，独立 Git 与锁文件。
- [ ] 需求基线、架构 ADR、依赖与许可证锁、兼容矩阵。
- [ ] 可安装 Agent、FakeAdapter、UIA Adapter、OCR 可选 Adapter。
- [ ] 单 UiActor、联系人绑定、消息/方向/快照/去重、持久游标。
- [ ] 事件缓存/补交、聚合、语音转写、人工接管。
- [ ] Spring AI 回复、管理台 DRAFT、RAG/权限/来源、受控 Tool。
- [ ] ReplyPolicy、SendGuard、审批/发送/回执/UNCERTAIN reconcile。
- [ ] OFF/DRAFT/AUTO 及有效模式原因、急停、限速与失效处理。
- [ ] 定时行情/订阅/日历/misfire/任务幂等。
- [ ] OpenAPI/JSON Schema、Java/Python DTO、数据库/SQLite 迁移。
- [ ] 测试夹具与报告、真实 Windows 验收、24h/8h 观察记录。
- [ ] 监控/脱敏日志/审计、部署脚本、备份恢复、runbook、升级回滚。
- [ ] 无明文密钥、真实客户截图/夹具或运行数据库进入仓库。
- [ ] 每项不支持/未验能力明确说明；AUTO 只开放已验联系人与意图。

### 11.2 实施时确认，不阻止需求文档交付

| 事项 | 默认/处理方法 | 最迟确认阶段 |
|---|---|---|
| 项目名称与路径（已确认） | 后端 wechat-ai：F:\ideaProject\wechat-ai；前端 wechat-ai-web：F:\TraeProject\wechat-ai-web；第一阶段创建，不接入 mc-ai | 0 |
| F:路径及工具可用性 | 创建前实测，不删目标目录、不私自换路径 | 0 |
| Windows/微信版本、账号 UI 可见性、语言/DPI | 实测，不从上游宣传推定 | 0 |
| 测试账号/好友/固定文案与授权 | 只读先做，真实发送需明确测试范围 | 0/7 |
| 客户身份与项目授权 | 人工核实内部绑定，不能自动按昵称建权限 | 2/6 |
| 模型/embedding provider、数据区域、预算 | FakeModel 先开发，真实 provider 配置化 | 4/5 |
| 授权知识文档、版本/有效期 | 合成黄金集先测，未授权资料不导入 | 5 |
| 行情接口、使用许可、地区规格口径、时效 | FixtureProvider 先实现，不进入真实 AUTO | 6/8 |
| 订阅同意、工作/交易日历、业务时间 | 无日历暂停定时，默认不向客户主动通知 | 8 |
| 保留期、备份区、告警接收目标 | 候选值见本文，正式运行前业务负责人确认 | 10 |
| 真实 UI 工具/桌面权限是否可用 | Codex 完成可测试代码；缺环境写人工步骤与未验 | 各相关阶段 |

## 12. 资料来源与事实边界

资料核查日期：2026-10-03。以下来源用于验证上游能力、维护状态与框架特性；本需求中的业务状态机、阈值、目录、接口和测试门槛为本项目设计，不能误写成上游保证。

| 主题 | 一手来源 | 本文采用范围 |
|---|---|---|
| 首选 RPA 项目 | [pywechat 仓库](https://github.com/Hello-Mr-Crab/pywechat) | pyweixin 功能分类与候选底座 |
| 安装与版本区分 | [QuickStart](https://github.com/Hello-Mr-Crab/pywechat/blob/main/QuickStart.md) | Windows/Python 说明、发行名与模块区分 |
| UI 可见性限制 | [微信 4.1+ 说明](https://github.com/Hello-Mr-Crab/pywechat/blob/main/Weixin4.0.md) | 必须先做本机探测，不能保证任意账号 |
| 上游授权文件 | [LICENSE](https://github.com/Hello-Mr-Crab/pywechat/blob/main/LICENSE) | LGPL 2.1 标注，分发检查锁定全文 |
| 兼容性故障参考 | [pywechat Issues](https://github.com/Hello-Mr-Crab/pywechat/issues) | 实测用例线索，用户报告不是因果证明 |
| OCR 参考 | [wechat-ai-reply](https://github.com/ai4evt/wechat-ai-reply) | 截图/OCR/解析分层，仅参考，不采用零风险宣传 |
| 定时/搜索参考 | [easyChat](https://github.com/LTEnjoy/easyChat) | 版本与错发修复记录、定时任务案例 |
| wxauto 范围 | [wxauto](https://github.com/cluic/wxauto) | README 用途限制，不作为主生产底座 |
| wxauto4 维护 | [wxauto4](https://github.com/cluic/wxauto4) | README 停止更新，不作为新主底座 |
| UI Automation 实现库 | [pywinauto 文档](https://pywinauto.readthedocs.io/en/latest/) | Windows UI 自动化基础能力 |
| AI 框架/Boot 兼容 | [Spring AI 入门](https://docs.spring.io/spring-ai/reference/getting-started.html) | BOM、Boot 兼容范围，部署时锁定版本 |
| RAG 框架 | [Spring AI RAG](https://docs.spring.io/spring-ai/reference/api/retrieval-augmented-generation.html) | 检索与 Advisor 能力 |
| Tool 框架 | [Spring AI Tool Calling](https://docs.spring.io/spring-ai/reference/api/tools.html) | Tool 定义、参数与可信上下文基础 |
| 向量库 | [pgvector](https://github.com/pgvector/pgvector) | PostgreSQL 向量检索扩展 |
| OCR 引擎 | [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) | 可选识别引擎，不等于微信适配器 |
| Windows GUI 部署 | [Microsoft Interactive Services](https://learn.microsoft.com/en-us/windows/win32/services/interactive-services) | 服务/交互用户会话限制 |
| Codex 项目指令 | [OpenAI AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md) | 仓库级执行约束与分层指令 |
| 前端新建工程 | [Vue Quick Start](https://vuejs.org/guide/quick-start.html)、[Vite Getting Started](https://vite.dev/guide/) | Vue/TypeScript 工程初始化、开发构建入口与 Node 兼容 |

本设计将第三方 UI 自动化作为可被限制、会随客户端变化的桌面能力来管理。规则与工具选型不构成平台授权或账号安全保证；自动化能否运行以及是否适合长期业务使用，必须以用户当前授权、平台条件和实际验收为边界。未来若迁移到官方支持的客服通道，保留后端消息、RAG、Tool、Policy 与审计，将 Agent Adapter 替换为相应官方接口即可。
