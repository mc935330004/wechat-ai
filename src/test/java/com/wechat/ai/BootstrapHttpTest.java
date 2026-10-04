package com.wechat.ai;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.test.context.SpringBootTest;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class BootstrapHttpTest {
    @Value("${local.server.port}")
    int port;

    @Test
    void bootstrapIsHealthyAndReadOnly() throws Exception {
        var client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();
        var status = get(client, "/api/v1/admin/status");
        assertEquals(200, status.statusCode());
        assertTrue(status.body().contains("\"appName\":\"wechat-ai\""));
        assertTrue(status.body().contains("\"effectiveMode\":\"OFF\""));
        assertTrue(status.body().contains("\"schemaVersion\":1"));
        var health = get(client, "/actuator/health");
        assertEquals(200, health.statusCode());
        assertTrue(health.body().contains("\"status\":\"UP\""));
        assertEquals(404, get(client, "/actuator/env").statusCode());
    }

    private HttpResponse<String> get(HttpClient client, String path) throws Exception {
        var request = HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + port + path))
                .timeout(Duration.ofSeconds(10)).GET().build();
        return client.send(request, HttpResponse.BodyHandlers.ofString());
    }
}
