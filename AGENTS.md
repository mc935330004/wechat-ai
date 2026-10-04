# wechat-ai

- New independent backend; do not read or modify mc-ai.
- Frontend: F:\TraeProject\wechat-ai-web. API source: docs/contracts/openapi.yaml.
- Use Java 17, Maven Wrapper and scripts/dev.ps1. Default service is loopback-only/OFF.
- Keep external AI/database/RAG dependencies opt-in; never commit secrets or runtime data.
- Follow requirements.md for later phases. All future GUI writes must go through SendGuard.
- No Hook, DLL injection, reverse-engineered WeChat protocols or database decryption.
- Do not add abstractions or business modules before their implementation phase.
- Verify relevant behavior; distinguish real desktop checks from simulation.
