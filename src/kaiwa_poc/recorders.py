from __future__ import annotations

from pipecat.frames.frames import (
    Frame,
    InterimTranscriptionFrame,
    InterruptionFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMTextFrame,
    TranscriptionFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from .domain import SessionRuntime


class UserTurnRecorder(FrameProcessor):
    def __init__(self, session: SessionRuntime) -> None:
        super().__init__()
        self._session = session

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if isinstance(frame, TranscriptionFrame) and not isinstance(
            frame, InterimTranscriptionFrame
        ):
            self._session.add_turn("user", frame.text)
        await self.push_frame(frame, direction)


class AssistantTurnRecorder(FrameProcessor):
    def __init__(self, session: SessionRuntime) -> None:
        super().__init__()
        self._session = session
        self._active = False
        self._chunks: list[str] = []

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if isinstance(frame, (InterruptionFrame, LLMFullResponseStartFrame)):
            self._active = isinstance(frame, LLMFullResponseStartFrame)
            self._chunks.clear()
        elif self._active and isinstance(frame, LLMTextFrame):
            self._chunks.append(frame.text)
        elif self._active and isinstance(frame, LLMFullResponseEndFrame):
            self._session.add_turn("assistant", "".join(self._chunks))
            self._active = False
            self._chunks.clear()
        await self.push_frame(frame, direction)

    def discard_incomplete(self) -> None:
        self._active = False
        self._chunks.clear()

