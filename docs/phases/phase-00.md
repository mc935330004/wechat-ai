# Phase 0 执行记录

日期：2026-10-04。

最初用户授权范围：创建后台与前端项目，配置基础及后续可用 POM 依赖，确保正常启动。后续用户授权继续测试并指定测试会话，已开展只读 UIA/OCR 探测；真实测试消息由人工发送，工具没有发送入口。用户当前没有第二测试私聊，按一个已授权会话继续，双会话项暂缺。

## 已完成

- 创建 `F:\ideaProject\wechat-ai`，artifactId=wechat-ai，Java 包 com.wechat.ai。
- 创建 `F:\TraeProject\wechat-ai-web`，package name=wechat-ai-web。
- 两个目录分别初始化本地 Git，依赖、构建、README/AGENTS.md 独立；没有创建远程或推送。
- 后端 Spring Boot/Maven Wrapper；前端 Vue/TypeScript/Vite。
- 后端使用本机 JDK 17，前端独立 Node 22；运行环境记录与环境切换启动脚本。
- 核实用户已有 Python 3.14.8（64 位），路径 C:\Users\MC\AppData\Local\Programs\Python\Python314\python.exe；pip 26.2.1 与 venv 可用。
- 创建 agent/.venv，安装 pywechat127 1.9.8（pyweixin 模块）；导入与依赖检查通过，25 项运行依赖版本和来源哈希已锁定。
- 编写 agent/tools/probe.py 与可运行边界测试；完成真实微信 4.1.15.13 窗口探测，发现 UIA/Win32 子控件均为 0，消息读取被阻断。详细证据见 docs/compatibility.md、docs/acceptance/phase-00-report.md。
- 完成 agent/tools/ocr_probe.py、原生 OCR 对比入口、区域校准及 OCR 边界测试；本地 RapidOCR 两帧标题/已知输入标记精确匹配、快照一致性通过。RPA + OCR 当前 43 项依赖及 3 个模型哈希已锁定；详细证据见 docs/acceptance/ocr-readonly-report.md。
- 补充 OCR 人工测试标记的方向、同文重复、连续三条可见顺序验证入口；相关模拟边界检查与现有测试共 3 项通过。第一私聊已知短文字收发位置、同文两条保留、实际 A/B/C 可见顺序均有限验证通过，各检查两帧一致，失败证据保留。第二私聊待验。见 docs/acceptance/ocr-message-validation.md；未据此实现正式去重或聚合。
- 后端状态/健康接口、前端代理和连接检查页，有效模式固定 OFF。
- 完成 agent/tools/observe.py 低频只读观察入口，与已有测试共 4 项模拟边界检查通过。恢复窗口后真实 30 秒短测有限通过，2 轮 4 帧、跨度 30.001 秒、总耗时 43.247 秒；首次最小化失败保留，4 小时仍未执行，见 docs/acceptance/read-only-observation.md。
- 后端打包/真实 HTTP 测试、前端类型检查/构建/接口校验测试、浏览器成功/异常/重连与窄屏检查通过。
- 完整需求已保存为后端 requirements.md；接口真值在 docs/contracts/openapi.yaml，前端记录版本/hash。

## 未执行

- 账号和联系人稳定身份、第二测试私聊、任意消息正文准确率/方向/语音能力验证；UIA 不可读，OCR 原型仅通过标题、已知输入标记及第一私聊已知短文字收发位置读取。
- 受控微信测试发送、4 小时只读观察。
- 用户选择稍后运行 4 小时观察；当前没有长时间观察任务，已完成的短测记录保留。完整 Phase 0 仍未通过，不自动进入 AUTO。
- 模型、数据库与 RAG 的真实连接；POM 可选模块仅做依赖配置与解析检查。

当前结论：项目创建与默认启动验收通过；完整 Phase 0 的微信可行性验收尚未完成。后续按需求继续探测，不能据此启用 AUTO。

启动、构建、验收结果与回退见 README.md 和 docs/acceptance/project-bootstrap.md。默认服务仅绑定本机；当前没有业务鉴权/消息处理功能。
