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
                content = item.get("text") or item.get("content") or item.get("sentence") or ""
                if not str(content).strip():
                    continue
                start = item.get("start_time", item.get("start", idx * 10))
                end = item.get("end_time", item.get("end", float(start) + 10))
                speaker = item.get("speaker") or item.get("speaker_label") or item.get("channel")
                normalized.append(
                    TranscriptionSegment(
                        start_time=float(start or 0),
                        end_time=float(end or 0),
                        speaker=normalize_speaker(speaker, speaker_map),
                        content=str(content).strip(),
                    )
                )
        if normalized:
            return normalized

        text = payload.get("text") or payload.get("content") or payload.get("result", {}).get("text") or ""
        return [
            TranscriptionSegment(
                start_time=0,
                end_time=0,
                speaker="Speaker 1",
                content=str(text or "ASR API 未返回可解析文本").strip(),
            )
        ]

    def _find_segments(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        candidates = [
            payload.get("segments"),
            payload.get("data", {}).get("segments") if isinstance(payload.get("data"), dict) else None,
            payload.get("result", {}).get("segments") if isinstance(payload.get("result"), dict) else None,
        ]
        for candidate in candidates:
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
        return []


def get_asr_provider() -> ASRProvider:
    settings = get_settings()
    if settings.asr_provider.lower() == "mock":
        return MockASRProvider()
    return CustomASRProvider(settings)
