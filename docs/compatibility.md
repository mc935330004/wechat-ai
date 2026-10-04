# 本机 RPA 兼容性记录

日期：2026-10-04（Asia/Shanghai）。只读验证，未发送消息。

| 项目 | 本机证据 |
|---|---|
| Python | 3.14.8，x64，venv 与 pip 可用 |
| pywechat127 / pyweixin | 1.9.8，包下载、导入、pip check 通过 |
| pywinauto / comtypes / pywin32 | 0.6.9 / 1.4.17 / 312 |
| 微信 | 4.1.15.13 |
| 原生主窗口 | Qt51514QWindowIcon，可见、未最小化时仍复现不可读 |
| UIA 根节点 | Qt51514QWindowIcon，framework=Win32，children=0 |
| Win32 子窗口 | children=0 |
| 运行权限 | 微信与探测进程均未提权；本次未发现提权差异 |
| DPI、账号和稳定联系人身份 | UNVERIFIED |

安装包 SHA-256：`fcc3879a364c33ea4858ae28b4d7602677f0633979197963499d78ff1821313e`。25 项运行依赖已锁版本及来源哈希，并执行 `pip download --require-hashes --no-deps` 验证来源包可下载。部分依赖使用 sdist 构建，构建工具尚未作为发布环境完整锁定。

核对的上游 commit 为 `8589baa049bb91d3a500602c167f07b2f8397a13`；它是源码审阅基线，不能据此宣称 PyPI wheel 由该 commit 构建。实际安装以 PyPI wheel 哈希为准。[上游源码](https://github.com/Hello-Mr-Crab/pywechat/tree/8589baa049bb91d3a500602c167f07b2f8397a13)、[PyPI 1.9.8](https://pypi.org/project/pywechat127/1.9.8/)、[LGPL 2.1](https://github.com/Hello-Mr-Crab/pywechat/blob/8589baa049bb91d3a500602c167f07b2f8397a13/LICENSE)。

当前判定：**UIA 路线未准入，OCR 只读原型通过有限验证**。窗口能定位不等于 UIA 聊天内容可读；SDK 导入成功不等于该账号或客户端全部功能兼容。UIA 不可读的根因尚未确定，不能仅据此认定为账号限制或 Python 版本问题。

后续已执行 Phase 0/9 OCR 只读验证：Windows 原生中文 OCR 可用，但输入标记的下划线识别失败；最终使用本地 RapidOCR 3.9.2 + ONNX Runtime 1.30.0，两帧标题和已知输入标记精确匹配、快照一致，PASS。

本轮新增 18 项依赖，当前 RPA + OCR 共 43 项锁定；3 个模型来自安装包并锁哈希，使用显式本地路径。没有上传聊天图片；阻断 HTTP 发送的合成识别检查仍通过。

校准范围：微信 4.1.15.13、1100×800 客户端、DPI 120、浅色界面。稳定身份、收发方向、消息正文准确率、两测试私聊、语音及 4 小时证据仍未验，不能给出最终 GO_OCR_DRAFT 或完整 Phase 0 通过。保持 OFF，详见 docs/acceptance/ocr-readonly-report.md。
