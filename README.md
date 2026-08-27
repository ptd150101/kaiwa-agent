# Kaiwa Voice Agent PoC v0.1

PoC luyện hội thoại tiếng Nhật theo tình huống, dùng Pipecat làm realtime pipeline.

Luồng đang chạy trong v0.1:

```text
Browser microphone
  -> Pipecat SmallWebRTC
  -> Soniox streaming STT
  -> Kaiwa/Scenario LLM
  -> Soniox streaming TTS
  -> Browser speaker

Session end
  -> Language Coach LLM
  -> SQLite report + learner profile
```

## Phạm vi đã làm

- Realtime voice qua WebRTC và Pipecat development runner.
- Soniox `stt-rt-v5`, local VAD và barge-in do Pipecat xử lý.
- Soniox `tts-rt-v2`, giọng và tốc độ cấu hình bằng biến môi trường.
- LLM endpoint tương thích OpenAI; dùng được API cloud hoặc server local.
- Scenario có hai role tách biệt: role card của user và role/hidden facts của AI.
- Bốn scenario mẫu: ăn với đồng nghiệp, siêu thị, phỏng vấn và đổ xăng.
- Lưu transcript, báo cáo cuối buổi và learner profile trong SQLite.
- Language Coach chạy sau khi client ngắt kết nối; có fallback an toàn khi LLM lỗi.

Chưa có trong v0.1: second-pass ASR, forced alignment, chấm phát âm, giao diện chọn
scenario riêng, tài khoản người dùng và hạ tầng production.

## Chạy nhanh trên Windows PowerShell

Yêu cầu: Python 3.11–3.13, `uv`, microphone và Soniox API key.

```powershell
Copy-Item .env.example .env
notepad .env
uv sync --extra dev
uv run python -m kaiwa_poc.show_role
uv run python -m kaiwa_poc.bot -t webrtc
```

Mở `http://localhost:7860` (hoặc trực tiếp `/client`), cho phép dùng microphone rồi kết nối.

Sau khi kết thúc và ngắt kết nối, xem báo cáo:

```powershell
uv run python -m kaiwa_poc.report_cli
```

## Cấu hình LLM

API cloud tương thích OpenAI:

```dotenv
LLM_API_KEY=your-key
LLM_BASE_URL=
LLM_MODEL=gpt-4.1-mini
```

Server local tương thích OpenAI:

```dotenv
LLM_API_KEY=local
LLM_BASE_URL=http://127.0.0.1:8000/v1
LLM_MODEL=your-local-model
```

Realtime LLM nên trả first token nhanh và hỗ trợ streaming. Cùng một endpoint được dùng
cho Kaiwa Partner và Language Coach, nhưng hai vai có prompt và context tách biệt.

## Đổi scenario

Sửa `KAIWA_SCENARIO_ID` trong `.env` thành một trong các giá trị:

- `lunch_with_colleague_n4`
- `supermarket_n5`
- `job_interview_n3`
- `gas_station_n4`

Xem role card trước khi nói:

```powershell
uv run python -m kaiwa_poc.show_role
```

Role card chỉ chứa thông tin người học được phép biết. Hidden facts và hidden events chỉ
được đưa vào system prompt của nhân vật AI.

## Smoke test không cần API key

```powershell
$env:PYTHONPATH = "src"
python -m kaiwa_poc.text_demo
python -m unittest discover -s tests -v
```

Text demo chỉ kiểm tra scenario, transcript và persistence logic; nó không thay thế bài
kiểm tra voice end-to-end với Soniox.

## Tài liệu

- `docs/IMPLEMENTATION_PLAN.md`: roadmap và tiêu chí nghiệm thu chi tiết.
- `docs/poc-sequence.puml`: sequence PlantUML của PoC v0.1.
- `docs/VERIFICATION.md`: những gì đã/chưa được kiểm tra trong môi trường build.

## Ghi chú production

Development runner và SQLite chỉ dành cho PoC. Khi triển khai thật, thay bằng API/session
service riêng, PostgreSQL, Redis, object storage, background queue và WebRTC infrastructure
được quản lý phù hợp với tải thực tế.
