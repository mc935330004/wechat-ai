# 基础工程依赖记录

日期：2026-10-04。后端和前端为独立新建项目。

| 项目 | 锁定版本 | 锁定位置 |
|---|---|---|
| JDK | Oracle JDK 17.0.10+11-LTS-240 | docs/runtime-lock.json（已有本机安装目录） |
| Spring Boot | 4.1.1 | pom.xml parent；传递依赖由 Boot 管理 |
| Spring AI | 2.0.1 | pom.xml BOM；默认无模型连接 |
| Maven | 3.9.15 | .mvn/wrapper/maven-wrapper.properties |
| Python / RPA | Python 3.14.8 / pywechat127 1.9.8 | agent/dependency-lock.json、agent/requirements.lock；环境安装/导入通过，微信 UIA 读取未通过 |
| Node | 22.23.3 | 前端 docs/runtime-lock.json（来源、SHA-256、本机安装目录） |
| Vue | 3.5.43 | 前端 package.json/package-lock.json |
| Vite | 8.3.2 | 前端 package.json/package-lock.json |
| Vite Vue plugin | 6.0.9 | 前端 package.json/package-lock.json |
| TypeScript | 5.9.3 | 前端 package.json/package-lock.json |
| vue-tsc | 3.3.12 | 前端 package.json/package-lock.json |

默认后端有 Web MVC、Validation、Actuator、配置元数据、开发热重启、测试和可执行 jar 插件。ai/database/rag Maven profiles 中的版本统一由 Boot/Spring AI BOM 管理，不单独猜测传递依赖版本。

后续接入外部服务时记录最终有效依赖树与真实服务配置。依赖解析通过不能代替真实模型/数据库/RAG 验收。无需 Redis、Kafka、Lombok、前端组件库或路由库即可运行当前初始化版本。

本次已实际执行 `mvnw.cmd -Pai,database,rag dependency:resolve -DincludeScope=runtime`，所有可选运行依赖解析成功。

官方依据：

- [Spring Boot requirements](https://docs.spring.io/spring-boot/system-requirements.html)
- [Spring AI Getting Started](https://docs.spring.io/spring-ai/reference/getting-started.html)
- [Vite Getting Started](https://vite.dev/guide/)
- [Microsoft OpenJDK](https://learn.microsoft.com/en-us/java/openjdk/download)

后端使用本机已有 JDK 17；前端 .tools 中 Node 采用压缩包安装并校验 SHA-256。不修改全局 Java/Node 环境变量。项目迁移到其他机器时准备 JDK 17，并通过启动脚本 -JavaHome 指定路径；.tools 不提交到 Git。
