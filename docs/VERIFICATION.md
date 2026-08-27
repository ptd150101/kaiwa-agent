# Verification record — PoC v0.1

Ngày kiểm tra: 2026-08-26.

## Đã kiểm tra

- Dependency resolution bằng `uv`: thành công, lockfile có 108 packages.
- Pipecat runtime thực tế: `1.7.0` trên Python `3.12.13`.
- Ruff: tất cả checks passed.
- Pytest: 9 tests passed.
- Import toàn bộ bot và custom frame processors: thành công.
- Khởi tạo `SonioxSTTService`, `SonioxTTSService`, `OpenAILLMService` và
  `SileroVADAnalyzer`: thành công.
- Pipecat development runner khởi động ở chế độ WebRTC và báo `Bot ready`.
- Offline text demo: role card, transcript và safe fallback report được tạo đúng.

## Chưa thể kiểm tra trong môi trường build

- Audio end-to-end với Soniox STT/TTS vì không có API key của người dùng.
- Response thật của LLM endpoint do chưa có endpoint/key được cấu hình.
- Chất lượng tiếng Nhật, latency p50/p95 và hành vi barge-in trên thiết bị người dùng.

Các kiểm tra trên cần thực hiện sau khi sao chép `.env.example` thành `.env` và điền key.

