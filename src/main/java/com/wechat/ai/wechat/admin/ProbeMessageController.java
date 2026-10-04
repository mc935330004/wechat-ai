package com.wechat.ai.wechat.admin;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Profile;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

/** Local opt-in test receipt, not the production Agent gateway. */
@RestController
@Profile("dev")
@ConditionalOnProperty(name = "wechat.probe.enabled", havingValue = "true")
public class ProbeMessageController {
    private final byte[] token;
    // ponytail: bounded in-memory receipts for one controlled test; durable journal is Phase 2.
    private final LinkedHashMap<UUID, Receipt> receipts = new LinkedHashMap<>();

    public ProbeMessageController(@Value("${wechat.probe.token:}") String token) {
        if (token.length() < 32 || token.length() > 128) {
            throw new IllegalArgumentException("A 32..128 character probe token is required");
        }
        this.token = token.getBytes(StandardCharsets.UTF_8);
    }

    @PostMapping("/api/v1/dev/probe-messages")
    public synchronized Receipt receive(@RequestHeader(value = "X-Probe-Token", defaultValue = "") String supplied,
                                        @Valid @RequestBody ProbeMessage message, HttpServletRequest request) {
        authorize(supplied, request);
        var existing = receipts.get(message.eventId());
        if (existing != null) {
            if (!existing.message().equals(message)) {
                throw new ResponseStatusException(HttpStatus.CONFLICT);
            }
            return existing;
        }
        if (receipts.size() >= 64) {
            throw new ResponseStatusException(HttpStatus.TOO_MANY_REQUESTS);
        }
        var receipt = new Receipt(message, Instant.now(), "ACCEPTED", "OFF");
        receipts.put(message.eventId(), receipt);
        return receipt;
    }

    @GetMapping("/api/v1/dev/probe-messages")
    public synchronized List<Receipt> list(@RequestHeader(value = "X-Probe-Token", defaultValue = "") String supplied,
                                           HttpServletRequest request) {
        authorize(supplied, request);
        return List.copyOf(receipts.values());
    }

    private void authorize(String supplied, HttpServletRequest request) {
        if ((!request.getRemoteAddr().equals("127.0.0.1") && !request.getRemoteAddr().equals("::1")
                && !request.getRemoteAddr().equals("0:0:0:0:0:0:0:1"))
                || supplied.length() > 128
                || !MessageDigest.isEqual(token, supplied.getBytes(StandardCharsets.UTF_8))) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED);
        }
    }

    @ExceptionHandler({MethodArgumentNotValidException.class, HttpMessageNotReadableException.class})
    public ResponseEntity<Map<String, String>> invalidPayload() {
        // Never log or echo rejected message text, even on the test endpoint.
        return ResponseEntity.badRequest().body(Map.of("error", "INVALID_TEST_PAYLOAD"));
    }

    public record ProbeMessage(@NotNull UUID eventId, @NotNull UUID agentRunId,
                               @NotNull Instant observedAt,
                               @NotNull @Pattern(regexp = "WXPIPE20261004A") String text,
                               @NotNull @Pattern(regexp = "IN") String direction,
                               @NotNull @Pattern(regexp = "REAL_DESKTOP_OCR|SYNTHETIC") String evidenceSource) {}

    public record Receipt(ProbeMessage message, Instant receivedAt, String status, String effectiveMode) {}
}
