# Kế hoạch triển khai Kaiwa Voice Agent

## 1. Mục tiêu sản phẩm

Xây dựng voice agent giúp người Việt thực hành kaiwa tiếng Nhật theo free topic và tình
huống thực tế: đời sống, công sở, học hành, phỏng vấn, chợ/siêu thị, cây xăng, trường học,
ăn uống với đồng nghiệp và các chủ đề do người học tự nhập.

Ba giá trị chính:

1. Hội thoại đủ nhanh để có cảm giác đang nói chuyện với người thật.
2. AI luôn giữ đúng vai, trình độ và mục tiêu của scenario.
3. Feedback sau buổi có bằng chứng, không biến lỗi ASR thành lỗi của người học.

## 2. Actor và agent

| Thành phần | Loại | Có dùng LLM | Trách nhiệm |
|---|---|---:|---|
| Human User | Actor | Không | Nhập vai theo User Role Card và nói tiếng Nhật |
| Kaiwa Partner | Logical agent | Có | Đóng nhân vật đối thoại và trả lời realtime |
| Scenario Director | Logical agent | Có | Tạo/điều chỉnh vai, mục tiêu, checkpoint và sự kiện ẩn |
| Language Coach | Logical agent | Có | Chấm ngôn ngữ và tạo feedback tiếng Việt sau buổi |
| Learner Model | Domain service | Không bắt buộc | Lưu tiến trình, lỗi lặp lại và nội dung nên ôn |
| Orchestrator | Deterministic service | Không | Quản lý session, state, timeout, retry và persistence |

Trong PoC, Kaiwa Partner và Scenario Director dùng chung một LLM call trên critical path.
Language Coach dùng cùng endpoint nhưng chạy một context riêng sau buổi. Learner Model là
SQLite + code xác định; không có “User LLM Agent” vì người thật đang đảm nhiệm vai user.

Chỉ thêm Simulated User Agent cho automated eval, tuyệt đối không chạy trong phiên học thật.

## 3. Stack chốt cho PoC v0.1

| Lớp | Lựa chọn | Lý do |
|---|---|---|
| Voice orchestration | Pipecat >= 1.7 | Pipeline realtime, interruption, VAD, provider adapters |
| Browser transport | SmallWebRTC + Pipecat development runner | Chạy local nhanh, không cần media server cloud cho PoC |
| Turn detection | Silero VAD + Pipecat endpointing | Barge-in và kết thúc lượt nói ở critical path |
| Realtime STT | Soniox `stt-rt-v5` | Có adapter Pipecat, streaming, Japanese và code-switching |
| Realtime TTS | Soniox `tts-rt-v2` | Streaming, chung API key và giảm số integration ban đầu |
| Realtime/Coach LLM | OpenAI-compatible endpoint | Không khóa provider; dùng được cloud hoặc local server |
| Scenario source | JSON có schema domain | Dễ review, version, test và không để LLM tự bịa toàn bộ |
| Session store | SQLite | Không cần hạ tầng ngoài trong PoC |
| Tests | unittest/pytest | Test domain không cần API key |

Các model local như ARK-ASR, Nemotron ASR, Qwen ASR, Qwen TTS, Audio8 TTS và OmniVoice
không bị loại bỏ. Chúng được đặt sau provider interface ở phase benchmark/self-host để PoC
đầu tiên không phải giải quyết đồng thời inference server, streaming adapter và sản phẩm.

## 4. Phạm vi PoC v0.1

### Có trong bản này

- Một phiên voice 1:1 trên browser.
- Một scenario được chọn qua environment variable.
- User Role Card chỉ chứa dữ liệu public.
- AI Role Card, hidden facts và hidden events chỉ nằm trong system prompt.
- STT → LLM → TTS streaming với interruption.
- Ghi lại final transcript của user và response hoàn chỉnh của assistant.
- Language Coach tạo JSON report khi client disconnect.
- Learner profile cập nhật số buổi và nhóm lỗi lặp lại.
- Bốn scenario seed để kiểm tra các register khác nhau.

### Không có trong bản này

- UI chọn topic/role/trình độ.
- Tạo free topic động bằng Scenario Director call riêng.
- Feedback card realtime.
- Second-pass ASR và forced alignment.
- Pronunciation score, pitch accent hoặc mora/phoneme timing.
- Auth, multi-tenant, thanh toán, admin CMS.
- Production autoscaling, queue và observability dashboard.

## 5. Ngân sách độ trễ mục tiêu

Các con số dưới đây là SLO kỹ thuật để benchmark, không phải cam kết của provider:

| Chặng | p50 mục tiêu | p95 mục tiêu |
|---|---:|---:|
| Phát hiện user dừng nói | <= 300 ms | <= 600 ms |
| Final transcript sau endpoint | <= 350 ms | <= 700 ms |
| LLM time-to-first-token | <= 500 ms | <= 1,000 ms |
| TTS time-to-first-audio | <= 350 ms | <= 700 ms |
| Speech-end → first bot audio | <= 1.3 s | <= 2.2 s |

Không đưa Coach, second-pass ASR hay forced alignment vào critical path.

## 6. Roadmap chi tiết

### Phase 0 — PoC voice loop, 2–3 ngày

Đầu việc:

- Thiết lập Pipecat runner + SmallWebRTC.
- Tích hợp Soniox STT/TTS và OpenAI-compatible LLM.
- Xây ScenarioSpec gồm user role, AI role, hidden facts, event và success conditions.
- Xây prompt giữ vai, giới hạn độ dài và không sửa bài giữa hội thoại.
- Lưu session/transcript/report vào SQLite.
- Tạo Coach async sau disconnect và rule fallback.
- Unit test schema, prompt boundary, persistence và coach fallback.

Điều kiện hoàn thành:

- Browser nói/nhận audio hai chiều được ít nhất 10 lượt.
- User có thể chen lời và bot dừng phát audio đang nói.
- Không có hidden fact trong User Role Card.
- Report được lưu dù Coach LLM lỗi.
- Test domain chạy không cần API key.

Trạng thái: đã được hiện thực trong project v0.1; cần người dùng điền API key để chạy E2E.

### Phase 1 — Product alpha, 1–2 tuần

Đầu việc:

- React/Next.js client dùng Pipecat Client SDK hoặc Voice UI Kit.
- Form chọn topic, JLPT, vai user, vai AI, thời lượng và feedback mode.
- Scenario Director call riêng trả `ScenarioContract` theo JSON Schema.
- Deterministic Scenario State Machine quản lý checkpoint và điều kiện kết thúc.
- API tạo/kết thúc/resume session; idempotency key cho mỗi turn.
- PostgreSQL thay SQLite; Redis giữ active session.
- Job queue cho Coach và report.
- Hiển thị transcript, task progress, correction cards và next drill.
- Bộ 30–50 scenario curated có review của giáo viên.

Điều kiện hoàn thành:

- User chọn scenario trên UI và thấy role card trước khi kết nối.
- Reconnect không tạo duplicate turn hoặc duplicate score.
- Kaiwa agent không tự đánh dấu checkpoint; Orchestrator validate state patch.
- Coach chỉ trích dẫn câu thực sự có trong transcript.

### Phase 2 — Speech analysis, 1–2 tuần

Đầu việc:

- Lưu audio theo từng user turn với chính sách retention rõ ràng.
- Second-pass ASR bằng Qwen3-ASR 0.6B/1.7B hoặc model thắng benchmark nội bộ.
- Chỉ chạy second pass cho turn confidence thấp hoặc turn được chọn để review.
- Forced alignment bằng Qwen3-ForcedAligner-0.6B trên audio + final transcript.
- Japanese normalization/G2P bằng MeCab + UniDic/OpenJTalk.
- Acoustic features: duration, pause, speech rate và F0 bằng Parselmouth/torchcrepe.
- UI phát lại đúng đoạn lỗi theo timestamp.

Luồng background:

```text
Turn audio + realtime transcript
  -> second-pass ASR
  -> choose final transcript with confidence/evidence
  -> forced alignment
  -> Japanese G2P + acoustic metrics
  -> pronunciation feedback
```

RTX 3060 12 GB: chạy tuần tự qua queue, không giữ đồng thời ASR, aligner, TTS và LLM lớn
trong VRAM. Có thể ưu tiên model 0.6B và unload sau job.

Điều kiện hoàn thành:

- Timestamp đủ chính xác để phát lại đúng từ/ký tự được chọn.
- Hệ thống không gọi lỗi ngữ pháp là lỗi phát âm.
- Turn có alignment confidence thấp bị loại khỏi pronunciation score.
- Có tập audio tiếng Nhật của người Việt để đo lỗi thay vì đánh giá cảm tính.

### Phase 3 — Provider benchmark và self-host, 1–2 tuần

Tạo adapter chuẩn:

```text
StreamingSTT.transcribe(audio_stream) -> partial/final/confidence
BatchASR.transcribe(turn_audio) -> transcript/timestamps/confidence
StreamingTTS.synthesize(text_stream) -> pcm_stream/word_timestamps
```

Benchmark STT: Soniox, ARK-ASR 3B/0.6B/0.1B, FunASR, Nemotron 3.5 ASR, Qwen ASR và
VibeVoice nếu model thực tế cung cấp đúng capability cần kiểm tra.

Benchmark TTS: Soniox, Audio8-TTS 0.6B, Qwen3-TTS và OmniVoice.

Dataset phải có:

- Người Việt nói tiếng Nhật N5–N3.
- Câu ngập ngừng, tự sửa, nói sai trợ từ và chia động từ.
- Tên riêng Nhật/Việt, số tiền, địa chỉ và code-switch.
- Môi trường phòng yên tĩnh và noise đời thực.

Chỉ số:

- STT: CER, entity accuracy, error-preservation rate, finalization latency.
- TTS: Japanese MOS, intelligibility, pronunciation of numbers/names, TTFA, RTF.
- Hệ thống: speech-end-to-first-audio, interruption success, GPU memory và cost/minute.

### Phase 4 — Production beta, 2–4 tuần

Đầu việc:

- Auth và tenant isolation.
- Production WebRTC layer; không dùng development runner.
- Session API, worker autoscaling và admission control.
- PostgreSQL, Redis, object storage và durable queue.
- OpenTelemetry traces xuyên suốt audio turn → ASR → LLM → TTS → Coach.
- Circuit breaker, timeout, retry policy và provider fallback.
- Audio consent, retention, export/delete và PII redaction.
- Prompt/version registry và eval gate trước deploy.
- Cost dashboard theo user, session, provider và model.

Điều kiện hoàn thành:

- Không mất report khi worker restart.
- Provider lỗi không làm hỏng session state.
- Có p50/p95 latency, error rate và cost/minute theo release.
- Có regression eval về giữ vai, độ khó, grammar feedback và hidden information.

## 7. Data contract cần giữ ổn định

### ScenarioContract

- `scenario_id`, `title`, `level`, `setting`
- `user_role`: identity, relationship, goals, known information
- `ai_role`: identity, relationship, personality, goals, hidden information
- `language_targets`, `hidden_events`, `success_conditions`
- Sau alpha: checkpoint graph, recovery policy, max turns và stop condition

### TurnEvidence

- `session_id`, `turn_id`, role, timestamps
- realtime transcript + confidence
- second-pass transcript + confidence (phase 2)
- audio object reference + retention status (phase 2)
- alignment spans + confidence (phase 2)
- model/provider/prompt versions

### SessionReport

- summary, strengths, corrections có original span
- task completed/missing
- grammar/vocabulary/politeness/naturalness/task scores
- pronunciation metrics chỉ khi có acoustic evidence
- next drill và limitations

## 8. Test strategy

### Unit

- Scenario parsing và ID uniqueness.
- Public role card không rò hidden facts/events.
- Kaiwa prompt chứa đủ hai vai và giới hạn output cho TTS.
- Session không ghi duplicate frame liên tiếp.
- SQLite round trip và profile aggregation.
- Coach JSON parser và safe fallback.

### Integration

- Mock STT/LLM/TTS qua Pipecat pipeline.
- Barge-in giữa response.
- Empty transcript, confidence thấp và provider timeout.
- Disconnect trong lúc LLM/TTS đang stream.
- Coach lỗi JSON hoặc endpoint local không hỗ trợ `response_format`.

### End-to-end

- 10 phiên cho mỗi scenario seed.
- Nói tự nhiên, ngập ngừng và code-switch.
- Đo latency từ audio end đến first bot audio.
- Review thủ công transcript và lời thoại bởi người học/giáo viên.

## 9. Rủi ro chính và cách kiểm soát

| Rủi ro | Kiểm soát |
|---|---|
| ASR tự sửa lỗi của người học | Lưu audio/realtime/second-pass riêng; Coach nêu confidence |
| LLM thoát vai hoặc nói quá dài | System prompt, max token, Scenario State Machine và eval |
| Hidden fact bị lộ | Public/private schema, unit test và output policy |
| Feedback bịa lỗi | Correction bắt buộc trỏ original span; không có span thì bỏ |
| Chấm phát âm sai | Chỉ chấm khi có alignment/acoustic evidence đủ confidence |
| RTX 3060 hết VRAM | Queue background, model 0.6B, unload tuần tự, cloud cho realtime |
| Development runner bị dùng nhầm production | Tách deployment profile và production readiness gate |

## 10. Việc nên làm ngay sau PoC

1. Điền Soniox/LLM key và chạy 20–30 phút trên hai scenario N4/N5.
2. Ghi lại p50/p95 speech-end-to-first-audio và transcript sai đáng chú ý.
3. Chọn 30 câu test tiếng Nhật của người Việt để tạo benchmark STT ban đầu.
4. Quyết định UI alpha và thiết kế `ScenarioContract` JSON Schema chính thức.
5. Chỉ sau khi realtime loop ổn định mới thêm second-pass ASR/forced alignment.
