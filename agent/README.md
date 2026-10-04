# RPA Agent

Phase 0 独立只读探测工具，位于 `F:\ideaProject\wechat-ai\agent`。不会打开会话、激活窗口、输入、发送、操作剪贴板或转写语音。

已建立 `.venv`，Python 3.14.8 x64；安装发行包 `pywechat127==1.9.8`，导入模块名 `pyweixin`，依赖检查和导入通过。运行依赖版本及来源哈希记录于 `requirements.lock`、`dependency-lock.json`；不参与 Maven/前端构建。

在后端根目录执行：

```powershell
# 仅核对环境和窗口，不读取聊天内容
& .\agent\.venv\Scripts\python.exe .\agent\tools\probe.py --read-only

# 手动恢复微信窗口并打开文件传输助手，然后读取脱敏测试快照
& .\agent\.venv\Scripts\python.exe .\agent\tools\probe.py --read-only --expected-chat '文件传输助手'

# 无真实桌面操作的边界检查
& .\agent\.venv\Scripts\python.exe -m unittest discover -s .\agent\tests -p 'test_*.py'
```

报告默认保存到 `agent/runtime/probe-latest.json`（Git 忽略），也可通过 `--output` 指定文件。退出码 0 表示已执行项目未出现 FAIL/BLOCKED，2 表示发现失败或阻断；UNVERIFIED 仍是未验，不等于整体准入通过。UIA 请求超过 30 秒结束探测子进程，不操作微信进程。

只有指定测试标题精确匹配时才读取消息。聊天内容不保留明文，仅保存长度、控件类别和使用临时随机密钥生成的 HMAC；同次探测可观察重复，不支持跨运行去重。账号、联系人稳定身份和 IN/OUT 尚未验证，保持 OFF。

当前实测：微信 4.1.15.13 主窗口可定位，但 UIA/Win32 子控件数均为 0。测试会话标题、消息与输入框无法读取；没有发送或启动上游 AutoReply/Monitor。不能声明 GO_UIA 或启用 AUTO。详见 `docs/compatibility.md` 与 `docs/acceptance/phase-00-report.md`。

## OCR 只读原型

UIA 不可读后，已增加本地 OCR 原型。默认使用 RapidOCR 3.9.2 + ONNX Runtime 1.30.0 CPU；模型来自安装包，运行时校验版本和模型 SHA-256，不在线下载模型或上传截图。Windows 自带 OCR 保留为对比入口，但本次输入标记的下划线识别失败，未作为默认方案。

```powershell
# 手动恢复微信，保持文件传输助手打开。测试文字由人工留在输入框，无需发送。
& .\agent\.venv\Scripts\python.exe -X utf8 .\agent\tools\ocr_probe.py --read-only --expected-chat '文件传输助手' --expected-input OCR_TEST_20261004

# 仅对比原生 OCR，结果单独保存，避免覆盖默认引擎报告
& .\agent\.venv\Scripts\python.exe -X utf8 .\agent\tools\ocr_probe.py --read-only --expected-chat '文件传输助手' --expected-input OCR_TEST_20261004 --engine windows --output .\agent\runtime\ocr-windows-comparison.json
```

当前 `ocr-layout.json` 只校准了微信 4.1.15.13、客户端区域 **1100×800 像素、DPI 120（125%）**、浅色界面。窗口尺寸、DPI 或版本变化会阻断，需重新人工校准；区域参数只用于读取截图。锁屏/非默认交互桌面、最小化、会话标题不精确匹配或标题置信度低于 0.9 时停止。仅忽略 OCR 分词空白，不纠正标题字符。

每次读取两帧。每帧的标题、聊天区域和输入区均来自同一截图，校验标题后才识别其余区域。OCR 行不是完整消息对象，不能据此断言 IN/OUT 或输入框为空。正文只保存长度、区域、置信度及随机密钥 HMAC；不保存明文或原始截图。临时截图放在忽略目录，探测结束清理；45 秒上限只终止本工具的子进程树。

真实测试：两帧标题和人工输入标记精确识别、快照一致性通过，系统保持 OFF。报告在 `agent/runtime/ocr-probe-latest.json`，验收说明见 `docs/acceptance/ocr-readonly-report.md`。两测试私聊、方向/重复消息、语音与 4 小时观察仍待验证。

RPA + OCR 共 43 项运行依赖已锁定，3 个 OCR 模型哈希记录在 `dependency-lock.json`。相关开源来源：[RapidOCR](https://github.com/RapidAI/RapidOCR)、[ONNX Runtime](https://github.com/microsoft/onnxruntime)、[Windows OCR API](https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr.ocrengine)。RapidOCR 源码采用 Apache 2.0；分发时一并保留相应许可证材料。

## 两测试私聊的人工标记验证

复用 OCR 探测入口，增加 `--message-check direction|duplicates|sequence`，不增加发送或导航能力。会话需人工打开，标记需人工发送/接收；仅指定标题精确匹配后才读聊天区。工具检查已知文字、置信度、位置与可见条数，重复文字必须位于两个不同的纵向行。所有标记仍需完整显示在已校准的聊天区域内。

方向重试可使用 `--message-check direction-b`，对应 B 组标记，排除旧 A 组对计数的影响；其匹配、方向和置信度要求相同。

```powershell
# 将会话名称替换为明确允许读取的测试私聊，不使用真实客户会话。
& .\agent\.venv\Scripts\python.exe -X utf8 .\agent\tools\ocr_probe.py --read-only --expected-chat '测试私聊名称' --message-check direction --output .\agent\runtime\direction-chat1.json
```

准备步骤、三轮标记与证据边界见 `docs/acceptance/ocr-message-validation.md`。消息正文仍只保留 HMAC、长度、位置和置信度；验证结果没有正文。按位置检查仅用于人工标注的测试文字，不能推广为任意消息的 IN/OUT 判定。正式监听、事件去重、连续消息聚合、稳定身份及 4 小时观察均未实现/验收，有效模式保持 OFF。

2026-10-04 第一私聊三项有限验证通过：B 组左侧接收/右侧发送、无后缀同文两条保留、实际 WXDUP 后缀 A/B/C 可见顺序，均精确识别且两帧一致。证据分别在 `agent/runtime/direction-chat1-b.json`、`duplicates-chat1-retry.json`、`sequence-dup-chat1.json`。实际 A/B/C 使用 `--message-check sequence-dup` 单独验证；此前失败记录保留。第二私聊未指定，正式监听、事件去重和聚合仍未完成。

## 低频只读观察

用户当前没有第二测试私聊，继续按一个已授权会话验证，双会话项暂缺。`tools/observe.py` 复用有界 OCR 探测，默认 60 秒、每 30 秒两帧，时长最多 4 小时；标题/布局不符、最小化/锁屏、失败或采样间隔过长时停止，不自动恢复。窗口仍需人工准备，工具保持 OFF。

```powershell
& .\agent\.venv\Scripts\python.exe -X utf8 .\agent\tools\observe.py --read-only --expected-chat '测试私聊名称' --duration-seconds 30 --interval-seconds 30 --output .\agent\runtime\observation-smoke-retry.json
```

报告仅存时间、耗时、标题匹配、快照一致性和可见行数，不存正文/截图/会话明文/HMAC；每轮临时报告自动清理。Ctrl+C 停止，所有后续轮询停止；工具只清理自身子进程树。恢复窗口后真实 30 秒短测通过：2 轮 4 帧、跨度 30.001 秒、总耗时 43.247 秒，见 `agent/runtime/observation-smoke-retry.json`；首轮最小化失败证据保留。模拟检查或短测通过不等于真实 4 小时通过，4 小时仍 UNVERIFIED。详见 `docs/acceptance/read-only-observation.md`。

重建环境（本机 Python 路径；更换机器时调整）：

```powershell
& 'C:\Users\MC\AppData\Local\Programs\Python\Python314\python.exe' -m venv .\agent\.venv
& .\agent\.venv\Scripts\python.exe -m pip install --require-hashes -r .\agent\requirements.lock
& .\agent\.venv\Scripts\python.exe -m pip check
```

`pywechat127` 源代码作为独立依赖安装，没有复制进业务代码。上游许可证为 [LGPL 2.1](https://github.com/Hello-Mr-Crab/pywechat/blob/8589baa049bb91d3a500602c167f07b2f8397a13/LICENSE)，分发时保留相应来源和许可证材料。
