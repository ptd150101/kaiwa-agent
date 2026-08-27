from __future__ import annotations

import asyncio

from dotenv import load_dotenv
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.soniox.stt import SonioxSTTService
from pipecat.services.soniox.tts import SonioxTTSService
from pipecat.transcriptions.language import Language
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.workers.runner import WorkerRunner

from .coach import RuleBasedCoach, create_coach
from .config import AppSettings
from .domain import SessionRuntime
from .prompts import build_kaiwa_system_prompt
from .recorders import AssistantTurnRecorder, UserTurnRecorder
from .repository import SessionRepository
from .scenario_catalog import ScenarioCatalog

load_dotenv(override=False)


transport_params = {
    "webrtc": lambda: TransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
    ),
}


async def run_bot(transport: BaseTransport) -> None:
    settings = AppSettings.from_env()
    settings.validate_voice_runtime()

    catalog = ScenarioCatalog.load()
    scenario = catalog.get(settings.scenario_id)
    repository = SessionRepository(settings.db_path)
    profile = repository.get_profile(settings.user_id, settings.level)
    session = SessionRuntime.create(
        user_id=settings.user_id,
        scenario=scenario,
        feedback_mode=settings.feedback_mode,
    )
    repository.save_session(session)

    logger.info("Session ID: {}", session.session_id)
    logger.info("\n{}", scenario.public_role_card())

    stt = SonioxSTTService(
        api_key=settings.soniox_api_key,
        vad_force_turn_endpoint=True,
        settings=SonioxSTTService.Settings(
            model=settings.soniox_stt_model,
            language_hints=[Language.JA],
            language_hints_strict=False,
        ),
    )
    tts = SonioxTTSService(
        api_key=settings.soniox_api_key,
        settings=SonioxTTSService.Settings(
            model=settings.soniox_tts_model,
            voice=settings.soniox_tts_voice,
            language=Language.JA,
            speed=settings.soniox_tts_speed,
        ),
    )
    llm = OpenAILLMService(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        settings=OpenAILLMService.Settings(
            model=settings.llm_model,
            system_instruction=build_kaiwa_system_prompt(scenario, profile),
            temperature=settings.llm_temperature,
            max_completion_tokens=120,
        ),
    )

    context = LLMContext()
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),
    )
    user_recorder = UserTurnRecorder(session)
    assistant_recorder = AssistantTurnRecorder(session)

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            user_recorder,
            user_aggregator,
            llm,
            assistant_recorder,
            tts,
            transport.output(),
            assistant_aggregator,
        ]
    )
    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(
            enable_metrics=settings.metrics_enabled,
            enable_usage_metrics=settings.metrics_enabled,
        ),
    )

    finalize_lock = asyncio.Lock()
    client_connected = False

    async def finalize(reason: str) -> None:
        async with finalize_lock:
            if session.finalized:
                return
            assistant_recorder.discard_incomplete()
            session.finish()
            repository.save_session(session)
            try:
                report = await create_coach(settings).assess(session)
            except Exception as exc:
                logger.exception("LLM Coach failed; saving a safe fallback report: {}", exc)
                report = await RuleBasedCoach().assess(session)
                report.setdefault("limitations", []).append(
                    f"LLM Coach failed: {type(exc).__name__}"
                )
            repository.save_report_and_update_profile(session, report)
            logger.info(
                "Finalized session {} ({}) with {} turns",
                session.session_id,
                reason,
                len(session.turns),
            )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client) -> None:
        nonlocal client_connected
        client_connected = True
        logger.info("Voice client connected")
        context.add_message(
            {
                "role": "developer",
                "content": (
                    "Bắt đầu tình huống ngay bây giờ bằng lời thoại tự nhiên trong vai của bạn. "
                    "Không đọc role card và không giải thích luật chơi."
                ),
            }
        )
        await worker.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client) -> None:
        logger.info("Voice client disconnected")
        await finalize("client_disconnected")
        await worker.cancel()

    runner = WorkerRunner(handle_sigint=False)
    await runner.add_workers(worker)
    try:
        await runner.run()
    finally:
        if client_connected:
            await finalize("runner_stopped")


async def bot(runner_args: RunnerArguments) -> None:
    """Pipecat development-runner entry point."""
    transport = await create_transport(runner_args, transport_params)
    await run_bot(transport)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()

