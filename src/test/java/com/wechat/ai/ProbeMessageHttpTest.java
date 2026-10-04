package com.wechat.ai;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.test.context.SpringBootTest;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = {"wechat.probe.enabled=true", "wechat.probe.token=synthetic-test-token-0123456789abcdef"})
class ProbeMessageHttpTest {
    private static final String TOKEN = "synthetic-test-token-0123456789abcdef";
    @Value("${local.server.port}") int port;
    private final HttpClient client = HttpClient.newHttpClient();

    @Test
    void localCanaryIsAuthenticatedValidatedAndIdempotent() throws Exception {
        String event = UUID.randomUUID().toString();
        String payload = """
                {"eventId":"%s","agentRunId":"%s","observedAt":"2026-10-04T00:00:00Z",
                 "text":"WXPIPE20261004A","direction":"IN","evidenceSource":"SYNTHETIC"}
                """.formatted(event, UUID.randomUUID());
        assertEquals(401, post(payload, "").statusCode());
        assertEquals(400, post(payload.replace("WXPIPE20261004A", "other customer text"), TOKEN).statusCode());
        assertEquals(400, post(payload.replace("\"IN\"", "\"OUT\""), TOKEN).statusCode());
        var accepted = post(payload, TOKEN);
        assertEquals(200, accepted.statusCode());
        assertTrue(accepted.body().contains("\"effectiveMode\":\"OFF\""));
        assertEquals(accepted.body(), post(payload, TOKEN).body());
        assertEquals(409, post(payload.replace("2026-10-04T00:00:00Z", "2026-10-04T00:00:01Z"), TOKEN).statusCode());
        var listed = client.send(HttpRequest.newBuilder(url()).header("X-Probe-Token", TOKEN).GET().build(),
                                 HttpResponse.BodyHandlers.ofString());
        assertEquals(200, listed.statusCode());
        assertEquals(1, listed.body().split("\"eventId\"", -1).length - 1);
        assertTrue(listed.body().contains(event));
    }

    private URI url() { return URI.create("http://127.0.0.1:" + port + "/api/v1/dev/probe-messages"); }
    private HttpResponse<String> post(String body, String token) throws Exception {
        return client.send(HttpRequest.newBuilder(url()).header("Content-Type", "application/json")
                .header("X-Probe-Token", token).POST(HttpRequest.BodyPublishers.ofString(body)).build(),
                HttpResponse.BodyHandlers.ofString());
    }
}
