package com.wechat.ai.wechat.admin;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class StatusController {
    @GetMapping("/api/v1/admin/status")
    public BootstrapStatus status() {
        // ponytail: bootstrap is read-only/OFF; implement mode transitions with authorization later.
        return new BootstrapStatus("wechat-ai", "UP", "OFF", 1);
    }

    public record BootstrapStatus(String appName, String status, String effectiveMode, int schemaVersion) {}
}
