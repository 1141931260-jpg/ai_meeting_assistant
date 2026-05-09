import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel

from app.config import Settings, get_settings


class TranscriptionSegment(BaseModel):
    start_time: float
    end_time: float
    speaker: str | None = None
    content: str


class ASRProvider(ABC):
    @abstractmethod
    def transcribe(self, file_path: str, enable_speaker_diarization: bool = True) -> list[TranscriptionSegment]:
        raise NotImplementedError


def normalize_speaker(value: Any, speaker_map: dict[str, str] | None = None) -> str:
    speaker_map = speaker_map if speaker_map is not None else {}
    raw = str(value or "Speaker 1").strip()
    if raw in speaker_map:
        return speaker_map[raw]
    match = re.search(r"(\d+)", raw)
    if raw.lower().startswith("speaker") and match:
        label = f"Speaker {int(match.group(1))}"
    else:
        label = f"Speaker {len(speaker_map) + 1}"
    speaker_map[raw] = label
    return label


class MockASRProvider(ASRProvider):
    def transcribe(self, file_path: str, enable_speaker_diarization: bool = True) -> list[TranscriptionSegment]:
        speakers = ["Speaker 1", "Speaker 2", "Speaker 3"] if enable_speaker_diarization else ["Speaker 1"] * 6
        contents = [
            "我们今天确认登录模块的改版目标，重点是降低新用户首次进入的理解成本。",
            "我这边建议先做短信验证码和企业微信登录，密码登录可以保留但不作为主入口。",
            "风险在于第三方登录审核周期不确定，可能影响下周联调。",
            "那就决定本周先完成短信验证码链路，下周接企业微信登录。",
            "我负责整理接口字段，周三前给前端一版稳定文档。",
            "我会在周五前完成前端页面和异常状态，优先级按高处理。",
        ]
        segments: list[TranscriptionSegment] = []
        for index, content in enumerate(contents):
            segments.append(
                TranscriptionSegment(
                    start_time=float(index * 12),
                    end_time=float(index * 12 + 10),
                    speaker=speakers[index % len(speakers)],
                    content=content,
                )
            )
        return segments


class CustomASRProvider(ASRProvider):
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def transcribe(self, file_path: str, enable_speaker_diarization: bool = True) -> list[TranscriptionSegment]:
        if not self.settings.asr_api_key or not self.settings.asr_api_base_url:
            return MockASRProvider().transcribe(file_path, enable_speaker_diarization)

        url = self.settings.asr_api_base_url.rstrip("/")
        headers = {"Authorization": f"Bearer {self.settings.asr_api_key}"}
        data = {
            "model": self.settings.asr_model,
            "enable_speaker_diarization": str(enable_speaker_diarization).lower(),
            "speaker_diarization": str(enable_speaker_diarization).lower(),
            "diarization": str(enable_speaker_diarization).lower(),
            "enable_diarization": str(enable_speaker_diarization).lower(),
        }
        path = Path(file_path)
        try:
            with path.open("rb") as handle:
                files = {"file": (path.name, handle, "application/octet-stream")}
                with httpx.Client(timeout=self.settings.ai_request_timeout) as client:
                    response = client.post(url, headers=headers, data=data, files=files)
                    response.raise_for_status()
                    payload = response.json()
        except Exception as exc:
            raise RuntimeError(f"ASR API 调用失败：{exc}") from exc
        return self._normalize_payload(payload)

    def _normalize_payload(self, payload: dict[str, Any]) -> list[TranscriptionSegment]:
        segments = self._find_segments(payload)
        speaker_map: dict[str, str] = {}
        normalized: list[TranscriptionSegment] = []
        if segments:
            for idx, item in enumerate(segments):
                content = self._segment_text(item)
                if not str(content).strip():
                    continue
                start = self._segment_time(item, ["start_time", "start", "begin", "from"], float(idx * 10))
                end = self._segment_time(item, ["end_time", "end", "stop", "to"], start + 10)
                speaker = self._segment_speaker(item)
                normalized.append(
                    TranscriptionSegment(
                        start_time=start,
                        end_time=end,
                        speaker=normalize_speaker(speaker, speaker_map),
                        content=str(content).strip(),
                    )
                )
        if normalized:
            return normalized

        word_segments = self._segments_from_words(self._find_words(payload), speaker_map)
        if word_segments:
            return word_segments

        result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
        text = payload.get("text") or payload.get("content") or result.get("text") or ""
        return [
            TranscriptionSegment(
                start_time=0,
                end_time=0,
                speaker="Speaker 1",
                content=str(text or "ASR API 未返回可解析文本").strip(),
            )
        ]

    def _find_segments(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        return self._find_named_list(payload, {"segments", "utterances", "sentences", "transcripts", "paragraphs"})

    def _find_words(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        return self._find_named_list(payload, {"words", "word_segments"})

    def _find_named_list(self, value: Any, names: set[str]) -> list[dict[str, Any]]:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in names and isinstance(item, list):
                    rows = [row for row in item if isinstance(row, dict)]
                    if rows:
                        return rows
            for item in value.values():
                rows = self._find_named_list(item, names)
                if rows:
                    return rows
        if isinstance(value, list):
            for item in value:
                rows = self._find_named_list(item, names)
                if rows:
                    return rows
        return []

    def _segment_text(self, item: dict[str, Any]) -> str:
        for key in ["text", "content", "sentence", "utterance", "transcript"]:
            value = item.get(key)
            if value:
                return str(value)
        words = item.get("words")
        if isinstance(words, list):
            return "".join(str(word.get("word") or word.get("text") or "") for word in words if isinstance(word, dict))
        return ""

    def _segment_speaker(self, item: dict[str, Any]) -> Any:
        for key in ["speaker", "speaker_label", "speaker_id", "speakerId", "speaker_name", "speakerName", "role", "participant", "channel", "channel_id"]:
            value = item.get(key)
            if value is not None and str(value).strip():
                return value
        return None

    def _segment_time(self, item: dict[str, Any], keys: list[str], fallback: float) -> float:
        for key in keys:
            if item.get(key) is not None:
                return float(item.get(key) or 0)
            ms_key = f"{key}_ms"
            if item.get(ms_key) is not None:
                return float(item.get(ms_key) or 0) / 1000
        return fallback

    def _segments_from_words(self, words: list[dict[str, Any]], speaker_map: dict[str, str]) -> list[TranscriptionSegment]:
        segments: list[TranscriptionSegment] = []
        current_speaker: str | None = None
        current_words: list[str] = []
        start_time = 0.0
        end_time = 0.0
        for index, word in enumerate(words):
            raw_speaker = self._segment_speaker(word)
            speaker = normalize_speaker(raw_speaker, speaker_map)
            text = str(word.get("word") or word.get("text") or "").strip()
            if not text:
                continue
            word_start = self._segment_time(word, ["start_time", "start", "begin"], float(index))
            word_end = self._segment_time(word, ["end_time", "end", "stop"], word_start)
            if current_speaker and speaker != current_speaker:
                segments.append(
                    TranscriptionSegment(start_time=start_time, end_time=end_time, speaker=current_speaker, content="".join(current_words))
                )
                current_words = []
                start_time = word_start
            if not current_speaker or speaker != current_speaker:
                current_speaker = speaker
                start_time = word_start
            current_words.append(text)
            end_time = word_end
        if current_speaker and current_words:
            segments.append(
                TranscriptionSegment(start_time=start_time, end_time=end_time, speaker=current_speaker, content="".join(current_words))
            )
        return segments


def get_asr_provider() -> ASRProvider:
    settings = get_settings()
    if settings.asr_provider.lower() == "mock":
        return MockASRProvider()
    return CustomASRProvider(settings)
