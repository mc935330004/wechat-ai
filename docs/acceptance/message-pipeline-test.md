# 桌面微信收到测试消息 → 后台接收凭证

日期：2026-10-04。目的：真实验证一条**新收到的固定测试文字**能够从微信桌面经本地 OCR Agent 传到本项目 Spring Boot 后台。没有数据库、AI 调用或微信自动发送。

## 范围

- 当前仅支持人工打开、明确允许读取的单个测试私聊，窗口布局沿用 OCR 校准。其他未打开会话、未读红点、群聊、任意正文、历史补读、语音和多行气泡不属于本轮能力。
- 只识别 `WXPIPE20261004A`，要求左侧、置信度至少 0.9、两帧各一次。标题精确匹配后才识别正文，原始截图和其他正文不落盘、不上报。
- 启动先建立标记不存在的基线，再等待对方发送。已存在的标记不能当新消息；重复标记或错方向会阻断。工具每轮间隔至少 15 秒，实际 OCR 探测还需约 10—15 秒，接收可能延迟几十秒。
- 该联调是 OFF 模式下明确启用的诊断入口。正式业务仍 OFF；不能据此声明正式多会话监听、可靠消息 ID、跨帧去重或连续消息聚合通过。

## 实际怎么测

1. 先启动本项目的临时测试后台（默认端口 8997，不占用当前开发配置 8996），手动打开已授权测试私聊，保持微信恢复、大小不变、桌面解锁。
2. 启动 Agent。看到 **ARMED** 后，请对方用自己的微信账号发一条独立文字 `WXPIPE20261004A`。发送前不要在聊天区已有该标记；工具不会代发。
3. 保持会话打开，等待 Agent 返回 **RECEIVED_BY_BACKEND**。查看后台凭证：`status=ACCEPTED`、`direction=IN`、`evidenceSource=REAL_DESKTOP_OCR`、正文等于测试文字，事件 ID 与 Agent 报告相同。这才算真实联调通过。

在 `F:\ideaProject\wechat-ai` 执行：

```powershell
# 首次或改代码后先打包；打包前停止占用该 jar 的自有测试实例。
& .\scripts\dev.ps1 -Action package

# 单独启动有本地令牌保护的测试实例，日志/PID/令牌位于忽略 Git 的 runtime。
& .\scripts\probe-backend.ps1 -Action start
Invoke-RestMethod http://127.0.0.1:8997/actuator/health

# 先不要发标记，等终端显示 ARMED。
& .\agent\.venv\Scripts\python.exe -X utf8 .\agent\tools\receive_test.py --read-only --expected-chat '已授权测试私聊名称'

# 接收到后台后核对凭证；不会把令牌打印到终端。
& .\scripts\probe-backend.ps1 -Action receipts

# 测试完关闭临时后台（只核对并停止脚本记录的自身进程）。
& .\scripts\probe-backend.ps1 -Action stop
```

Agent 默认最多运行 180 秒，允许 `--duration-seconds 60..600`；Ctrl+C 停止。程序到期不会继续读取。默认报告 `agent/runtime/receive-test-latest.json`，只含固定公开测试文字、事件和回执，不含其他聊天内容或令牌。

## 后台入口与最小数据

`POST /api/v1/dev/probe-messages`，`GET /api/v1/dev/probe-messages`。仅 dev profile + `WECHAT_PROBE_ENABLED=true` 时存在，必须使用 `X-Probe-Token`；本地令牌至少 32 字符，由启动脚本生成。默认启动返回 404。

上报字段：`eventId`、`agentRunId`、`observedAt`、`text`（只能是固定标记）、`direction=IN`、`evidenceSource`（真实 OCR 或明确标记的 SYNTHETIC）。回执返回原事件、`receivedAt`、`status=ACCEPTED`、`effectiveMode=OFF`。接口契约在 `docs/contracts/openapi.yaml`。

只保存最多 64 条内存凭证，后台重启后清空。同事件 ID、同内容重试返回原凭证；同 ID 改内容返回 409，容量满返回 429。Agent 网络重试复用同一事件 ID 和时间，不在微信重发；进程崩溃恢复和持久化幂等不在此原型范围。

## 失败定位

| 现象 | 检查与处理 |
|---|---|
| WINDOW_MINIMIZED / OCR_TITLE_MISMATCH / 布局变化 | 人工恢复正确窗口/会话/原尺寸；工具停止，不自动导航或恢复 |
| 后台 HTTP 404 | 确认连接的是已显式启用 probe 的实例，默认正常开发服务不开放该接口 |
| HTTP 401 | 确认 Agent 和后台使用同一 `runtime/probe-token.txt`；不把令牌贴到聊天或写入 Git |
| MARKER_ALREADY_VISIBLE | 未建立新消息基线；不要把历史消息计作新接收，重新测试需安排新的干净测试窗口/标记版本 |
| 右侧标记 / 多条相同标记 / 低置信度 | 检查对方实际发送与可见消息；工具不放宽方向、计数或字符匹配 |
| 检测成功但回执仍 pending | 查看测试后台健康和端口；同 ID 自动重试，超时报告保留 pending 事件，不能宣称后台已收到 |

## 验收记录

- Python 5 项模拟检查通过：基线存在则阻断、左侧证据校验、本地 URL 限制、回执校验、网络失败重试复用 ID、令牌不入报告。
- Java 2 项真实 HTTP 测试通过：默认入口关闭；启用后认证、受控正文验证、内存接收、同 ID 幂等和冲突处理。HTTP 测试中的 SYNTHETIC 不是真实微信收件。
- 临时 8997 实例健康 UP、初始凭证列表为空；当前 8996 开发服务保留。之前由本任务启动的 8080 实例因占用 jar 曾暂停，打包成功后已恢复 OFF；默认端口启动不开放诊断入口。打包已通过，拒绝的请求正文不会写入校验异常日志或响应。
- 真实桌面基线已通过并进入 ARMED；本轮最多 300 秒等待，实际 301.113 秒后停止，原因 TEST_TIMEOUT_OR_RECEIPT_PENDING，报告没有检测事件或接收回执，后台列表仍为空。完整真实桌面 → 后台尚未通过；下一轮必须先启动并等 ARMED，再人工发送新标记。
- 4 小时观察按用户选择暂缓，本轮不启动长时间观察，不启用 AUTO。
