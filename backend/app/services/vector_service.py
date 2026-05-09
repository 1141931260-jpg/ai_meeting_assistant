import os
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app import models
from app.config import get_settings
from app.services.embedding_provider import get_embedding_provider
from app.services.speaker_mapping_service import display_name_for_speaker


@dataclass
class VectorDocument:
    id: str
    content: str
    metadata: dict[str, Any]


MAX_VECTOR_TEXT_CHARS = 500


class VectorService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.embedding_provider = get_embedding_provider()
        self._collection = None

    def _get_collection(self):
        if self._collection is not None:
            return self._collection
        os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
        except Exception as exc:
            raise RuntimeError("ChromaDB 未安装，请先安装 backend/requirements.txt") from exc
        client = chromadb.PersistentClient(
            path=str(self.settings.chroma_path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = client.get_or_create_collection(name=self._collection_name())
        return self._collection

    def _collection_name(self) -> str:
        suffix = "".join(
            character.lower() if character.isalnum() else "_" for character in self.settings.embedding_model
        ).strip("_")
        suffix = "_".join(part for part in suffix.split("_") if part)
        return f"meeting_documents_{suffix or 'default'}"[:63].rstrip("_")

    def build_meeting_index(self, db: Session, meeting_id: str) -> None:
        docs = self._collect_documents(db, meeting_id)
        if not docs:
            return
        embeddings = [self.embedding_provider.embed_texts([doc.content])[0] for doc in docs]
        collection = self._get_collection()
        ids = [doc.id for doc in docs]
        collection.upsert(
            ids=ids,
            documents=[doc.content for doc in docs],
            metadatas=[doc.metadata for doc in docs],
            embeddings=embeddings,
        )

    def search(self, db: Session, query: str, top_k: int) -> list[dict[str, Any]]:
        query_embedding = self.embedding_provider.embed_query(query)
        collection = self._get_collection()
        result = collection.query(query_embeddings=[query_embedding], n_results=top_k)
        rows: list[dict[str, Any]] = []
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0] if result.get("distances") else [0] * len(ids)
        for index, _id in enumerate(ids):
            metadata = dict(metadatas[index] or {})
            meeting = db.get(models.Meeting, metadata.get("meeting_id"))
            if not meeting:
                continue
            speaker = metadata.get("speaker")
            participant_name = None
            if speaker:
                participant_name, _participant_id = display_name_for_speaker(db, meeting.id, speaker)
            rows.append(
                {
                    "meeting_id": meeting.id,
                    "meeting_title": meeting.title,
                    "content_type": metadata.get("content_type", "segment"),
                    "speaker": speaker,
                    "participant_name": participant_name,
                    "content": documents[index],
                    "score": float(1 / (1 + distances[index])),
                    "evidence": metadata.get("evidence"),
                    "metadata": metadata,
                }
            )
        return rows

    def _collect_documents(self, db: Session, meeting_id: str) -> list[VectorDocument]:
        meeting = db.get(models.Meeting, meeting_id)
        if not meeting:
            return []
        docs: list[VectorDocument] = []
        for segment in meeting.transcript_segments:
            self._append_documents(
                docs,
                f"segment-{segment.id}",
                segment.content,
                {
                    "meeting_id": meeting_id,
                    "content_type": "segment",
                    "speaker": segment.speaker,
                    "evidence": segment.content[:160],
                },
            )
        if meeting.summary:
            self._append_documents(
                docs,
                f"summary-{meeting.summary.id}",
                f"{meeting.summary.overview}\n{meeting.summary.conclusion}",
                {"meeting_id": meeting_id, "content_type": "summary"},
            )
        for decision in meeting.decisions:
            self._append_documents(
                docs,
                f"decision-{decision.id}",
                decision.content,
                {
                    "meeting_id": meeting_id,
                    "content_type": "decision",
                    "speaker": decision.speaker,
                    "evidence": decision.evidence,
                },
            )
        for risk in meeting.risks:
            self._append_documents(
                docs,
                f"risk-{risk.id}",
                f"{risk.risk_type}: {risk.description}",
                {
                    "meeting_id": meeting_id,
                    "content_type": "risk",
                    "speaker": risk.speaker,
                    "evidence": risk.evidence,
                },
            )
        for action in meeting.action_items:
            self._append_documents(
                docs,
                f"action-{action.id}",
                f"{action.title}\n{action.description or ''}",
                {
                    "meeting_id": meeting_id,
                    "content_type": "action_item",
                    "speaker": action.source_speaker,
                    "evidence": action.evidence,
                },
            )
        return docs

    def _append_documents(self, docs: list[VectorDocument], base_id: str, content: str, metadata: dict[str, Any]) -> None:
        chunks = self._split_text(content)
        for index, chunk in enumerate(chunks):
            chunk_id = base_id if len(chunks) == 1 else f"{base_id}-{index + 1}"
            docs.append(
                VectorDocument(
                    id=chunk_id,
                    content=chunk,
                    metadata=self._clean_metadata(
                        {
                            **metadata,
                            "chunk_index": index,
                            "chunk_count": len(chunks),
                        }
                    ),
                )
            )

    def _split_text(self, text: str) -> list[str]:
        text = text.strip()
        if not text:
            return []
        return [text[index : index + MAX_VECTOR_TEXT_CHARS] for index in range(0, len(text), MAX_VECTOR_TEXT_CHARS)]

    def _clean_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in metadata.items() if value is not None}
