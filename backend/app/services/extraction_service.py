from sqlalchemy.orm import Session

from app import models
from app.services.llm_provider import get_llm_provider, parse_json_object
from app.services.summary_service import transcript_prompt_text


def extract_decisions(db: Session, meeting_id: str) -> list[models.Decision]:
    prompt = f"""
从会议转写中提取关键决策，只输出 JSON：
{{"decisions":[{{"content":"","owner":null,"reason":"","evidence":"","speaker":""}}]}}

会议转写：
{transcript_prompt_text(db, meeting_id)}
"""
    data = parse_json_object(get_llm_provider().generate(prompt), {"decisions": []})
    db.query(models.Decision).filter(models.Decision.meeting_id == meeting_id).delete()
    rows: list[models.Decision] = []
    for item in data.get("decisions") or []:
        row = models.Decision(
            meeting_id=meeting_id,
            content=str(item.get("content") or ""),
            owner=item.get("owner"),
            reason=item.get("reason"),
            evidence=item.get("evidence"),
            speaker=item.get("speaker"),
        )
        if row.content:
            db.add(row)
            rows.append(row)
    db.commit()
    return rows


def extract_risks(db: Session, meeting_id: str) -> list[models.Risk]:
    prompt = f"""
从会议转写中识别风险，只输出 JSON：
{{"risks":[{{"risk_type":"","description":"","level":"medium","owner":null,"speaker":"","evidence":"","suggestion":""}}]}}
level 只能是 low、medium、high。

会议转写：
{transcript_prompt_text(db, meeting_id)}
"""
    data = parse_json_object(get_llm_provider().generate(prompt), {"risks": []})
    db.query(models.Risk).filter(models.Risk.meeting_id == meeting_id).delete()
    rows: list[models.Risk] = []
    for item in data.get("risks") or []:
        level = item.get("level") if item.get("level") in {"low", "medium", "high"} else "medium"
        row = models.Risk(
            meeting_id=meeting_id,
            risk_type=str(item.get("risk_type") or "未分类风险"),
            description=str(item.get("description") or ""),
            level=level,
            owner=item.get("owner"),
            speaker=item.get("speaker"),
            evidence=item.get("evidence"),
            suggestion=item.get("suggestion"),
        )
        if row.description:
            db.add(row)
            rows.append(row)
    db.commit()
    return rows


def extract_action_items(db: Session, meeting_id: str) -> list[models.ActionItem]:
    prompt = f"""
从会议转写中提取行动项，只输出 JSON：
{{"action_items":[{{"title":"","description":"","owner":null,"due_date":null,"priority":"medium","status":"todo","evidence":"","source_speaker":""}}]}}
priority 只能是 low、medium、high；status 只能是 todo、doing、done。不确定负责人时返回 null。

会议转写：
{transcript_prompt_text(db, meeting_id)}
"""
    data = parse_json_object(get_llm_provider().generate(prompt), {"action_items": []})
    db.query(models.ActionItem).filter(models.ActionItem.meeting_id == meeting_id).delete()
    rows: list[models.ActionItem] = []
    for item in data.get("action_items") or []:
        priority = item.get("priority") if item.get("priority") in {"low", "medium", "high"} else "medium"
        status = item.get("status") if item.get("status") in {"todo", "doing", "done"} else "todo"
        row = models.ActionItem(
            meeting_id=meeting_id,
            title=str(item.get("title") or ""),
            description=item.get("description"),
            owner=item.get("owner"),
            due_date=item.get("due_date"),
            priority=priority,
            status=status,
            evidence=item.get("evidence"),
            source_speaker=item.get("source_speaker"),
        )
        if row.title:
            db.add(row)
            rows.append(row)
    db.commit()
    return rows
