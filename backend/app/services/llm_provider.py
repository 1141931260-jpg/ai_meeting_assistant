import json
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.config import Settings, get_settings


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        raise NotImplementedError


class MockLLMProvider(LLMProvider):
    def generate(self, prompt: str) -> str:
        lower = prompt.lower()
        if "会议问答助手" in prompt:
            question = prompt.split("【用户问题】")[-1].strip()
            return json.dumps(
                {
                    "answer": f"这是基于当前会议资料的模拟回答：你问的是“{question}”。请配置真实 LLM API 以获得更完整的会议内问答。"
                },
                ensure_ascii=False,
            )
        if "risk" in lower or "风险" in prompt:
            return json.dumps(
                {
                    "risks": [
                        {
                            "risk_type": "进度风险",
                            "description": "第三方登录审核周期不确定，可能影响联调节奏。",
                            "level": "medium",
                            "owner": None,
                            "speaker": "Speaker 3",
                            "evidence": "第三方登录审核周期不确定",
                            "suggestion": "提前准备短信验证码兜底方案。",
                        }
                    ]
                },
                ensure_ascii=False,
            )
        if "decision" in lower or "决策" in prompt:
            return json.dumps(
                {
                    "decisions": [
                        {
                            "content": "本周优先完成短信验证码登录链路，下周接入企业微信登录。",
                            "owner": None,
                            "reason": "先保证核心登录路径可用，降低外部审核依赖。",
                            "evidence": "本周先完成短信验证码链路，下周接企业微信登录。",
                            "speaker": "Speaker 1",
                        }
                    ]
                },
                ensure_ascii=False,
            )
        if "action" in lower or "行动项" in prompt or "任务" in prompt:
            return json.dumps(
                {
                    "action_items": [
                        {
                            "title": "整理登录接口字段",
                            "description": "输出前后端联调用的稳定接口文档。",
                            "owner": "Speaker 2",
                            "due_date": "周三",
                            "priority": "high",
                            "status": "todo",
                            "evidence": "周三前给前端一版稳定文档。",
                            "source_speaker": "Speaker 2",
                        },
                        {
                            "title": "完成前端登录页面和异常状态",
                            "description": "实现页面、加载状态和错误提示。",
                            "owner": "Speaker 3",
                            "due_date": "周五",
                            "priority": "high",
                            "status": "todo",
                            "evidence": "周五前完成前端页面和异常状态。",
                            "source_speaker": "Speaker 3",
                        },
                    ]
                },
                ensure_ascii=False,
            )
        return json.dumps(
            {
                "overview": "本次会议围绕登录模块改版展开，明确了优先路径、技术风险和近期交付任务。",
                "key_points": ["优先建设短信验证码登录", "企业微信登录放到下周接入", "第三方审核周期是主要风险"],
                "conclusion": "团队决定先交付可控的短信验证码链路，并同步准备企业微信接入。",
                "speaker_summary": {
                    "Speaker 1": "推动确认阶段性目标和最终决策。",
                    "Speaker 2": "负责接口字段和后端联调准备。",
                    "Speaker 3": "指出外部审核风险并承担前端交付。",
                },
            },
            ensure_ascii=False,
        )


class OpenAICompatibleLLMProvider(LLMProvider):
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def generate(self, prompt: str) -> str:
        if not self.settings.llm_api_key or not self.settings.llm_api_base_url:
            return MockLLMProvider().generate(prompt)

        url = f"{self.settings.llm_api_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": "你是严谨的会议纪要助手，只输出合法 JSON。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        try:
            with httpx.Client(timeout=self.settings.ai_request_timeout) as client:
                response = client.post(url, headers=headers, json=body)
                if response.status_code >= 400:
                    retry_body = dict(body)
                    retry_body.pop("response_format", None)
                    response = client.post(url, headers=headers, json=retry_body)
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            raise RuntimeError(f"LLM API 调用失败：{exc}") from exc
        return payload["choices"][0]["message"]["content"]


def parse_json_object(text: str, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return fallback
    return fallback


def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.llm_provider.lower() == "mock":
        return MockLLMProvider()
    return OpenAICompatibleLLMProvider(settings)
