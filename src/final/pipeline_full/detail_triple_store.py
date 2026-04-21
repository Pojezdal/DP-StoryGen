from __future__ import annotations

import json
import math
import re
from typing import Any, Dict, Iterable, List, Sequence

from .detail_triple_extraction import extract_detail_triples
from final.utils.serialization import StoryDirectory

from .schemas.detail_triples import DetailTriple


class DetailTripleStore:
    """Chapter-scoped detail triple cache loaded from extraction stage artifacts."""

    DEFAULT_STAGE_PREFIX = "detail_triple_extraction"

    def __init__(
        self,
        story_directory: StoryDirectory,
        stage_prefix: str = DEFAULT_STAGE_PREFIX,
    ):
        self.story_directory = story_directory
        self.stage_prefix = stage_prefix
        self._records: list[dict[str, Any]] = []
        self._loaded_chapters: set[int] = set()

    def load(
        self,
        start_chapter: int,
        end_chapter: int,
        *,
        extract_if_missing: bool = True,
        extraction_llm: Any | None = None,
        actors_context: Any = None,
    ):
        if start_chapter <= 0 or end_chapter <= 0 or end_chapter < start_chapter:
            return []

        for chapter_number in range(start_chapter, end_chapter + 1):
            self._ensure_chapter_loaded(
                chapter_number=chapter_number,
                extract_if_missing=extract_if_missing,
                extraction_llm=extraction_llm,
                actors_context=actors_context,
            )


    def select_for_next_chapter(
        self,
        next_chapter_package: Dict[str, Any],
        max_items: int = 50,
    ) -> List[Dict[str, Any]]:
        """Select the most relevant triples for the next chapter package.

        Two-stage selection strategy:
        1. Include all triples from the previous chapter first.
        2. Fill remaining capacity with top-scored triples from older chapters.
        """
        if max_items <= 0:
            return []

        next_chapter_number = next_chapter_package.get("chapter_meta", {}).get("chapter_number", None)
        chapter_number = next_chapter_number - 1 if next_chapter_number is not None else None

        package_tokens = self._build_package_tokens(next_chapter_package)
        temporal_relation = self._extract_temporal_relation(next_chapter_package)

        scored: List[tuple[float, Dict[str, Any]]] = []
        for record in self._records:
            score = self._score_record(
                record,
                next_chapter_number=next_chapter_number,
                temporal_relation=temporal_relation,
                package_tokens=package_tokens,
            )
            scored.append((score, record))

        recent_stage: List[tuple[float, Dict[str, Any]]] = []
        old_stage: List[tuple[float, Dict[str, Any]]] = []
        for score, record in scored:
            record_chapter = self._to_int(record.get("chapter"))
            if chapter_number is not None and record_chapter ==  chapter_number:
                recent_stage.append((score, record))
            else:
                old_stage.append((score, record))

        recent_stage.sort(key=lambda item: item[0], reverse=True)
        old_stage.sort(key=lambda item: item[0], reverse=True)

        if len(recent_stage) >= max_items:
            return [record for _, record in recent_stage[:max_items]]

        selected: List[Dict[str, Any]] = [record for _, record in recent_stage]
        remaining_capacity = max_items - len(selected)
        selected.extend(record for _, record in old_stage[:remaining_capacity])
        return selected

    def _ensure_chapter_loaded(
        self,
        *,
        chapter_number: int,
        extract_if_missing: bool,
        extraction_llm: Any | None = None,
        actors_context: Any = None,
    ) -> None:
        if chapter_number in self._loaded_chapters:
            return

        chapter_payload = self._extract_chapter_payload(
            chapter_number=chapter_number,
            extraction_llm=extraction_llm,
            actors_context=actors_context,
        )

        self._loaded_chapters.add(chapter_number)
        if chapter_payload is None:
            return

        self._records.extend(chapter_payload["records"])


    def _load_chapter_payload(self, chapter_number: int) -> Dict[str, Any] | None:
        stage_name = f"{self.stage_prefix}_{chapter_number:02d}"
        data, raw_output = self.story_directory.load_stage(stage_name)
        payload = raw_output or data.get("output", None)
        payload = json.loads(payload) if isinstance(payload, str) else payload
        if payload is None:
            return None
        return self._parse_chapter_payload(payload)


    def _extract_chapter_payload(
        self,
        *,
        chapter_number: int,
        extraction_llm: Any | None,
        actors_context: Any = None,
    ) -> Dict[str, Any] | None:
        if extraction_llm is None:
            return None

        _, chapter_text = self.story_directory.load_stage(f"chapter_generation_{chapter_number:02d}")

        if not chapter_text.strip():
            return None

        extracted = extract_detail_triples(
            llm=extraction_llm,
            story_directory=self.story_directory,
            chapter_text=chapter_text,
            chapter_number=chapter_number,
            actors_context=actors_context,
            stage_prefix=self.stage_prefix,
        )
        if not isinstance(extracted, dict):
            return None

        return self._parse_chapter_payload(extracted)

    def _parse_chapter_payload(
        self,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload["records"] = [
            self._normalize_record(record)
            for record in payload.get("records", [])
            if isinstance(record, dict)
        ]
        return payload


    @staticmethod
    def _normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "subject": str(record.get("subject", "")).strip(),
            "predicate": str(record.get("predicate", "")).strip(),
            "object": str(record.get("object", "")).strip(),
            "chapter": record.get("chapter", None),
            "chapter_text_hash": str(record.get("chapter_text_hash", "") or "").strip(),
            "evidence_snippet": str(record.get("evidence_snippet", "")).strip(),
            "fact_type": str(record.get("fact_type", "other") or "other").strip(),
            "subject_type": str(record.get("subject_type", "other") or "other").strip(),
            "continuity_window": str(record.get("continuity_window", "same_day") or "same_day").strip(),
        }

    @staticmethod
    def _deduplicate(records: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen: set[tuple[Any, ...]] = set()
        unique: List[Dict[str, Any]] = []

        for record in records:
            key = (
                record.get("subject", ""),
                record.get("predicate", ""),
                record.get("object", ""),
                record.get("chapter", None),
                record.get("chapter_text_hash", ""),
                record.get("evidence_snippet", ""),
                record.get("fact_type", "other"),
                record.get("subject_type", "other"),
                record.get("continuity_window", "same_day"),
            )
            if key in seen:
                continue

            seen.add(key)
            unique.append(record)

        unique.sort(
            key=lambda item: (
                DetailTripleStore._to_int(item.get("chapter")) or 0,
            )
        )
        return unique

    @staticmethod
    def _extract_next_chapter_number(next_chapter_package: Dict[str, Any]) -> int | None:
        chapter_meta = next_chapter_package.get("chapter_meta", {})
        chapter_number = chapter_meta.get("chapter_number", None)
        return DetailTripleStore._to_int(chapter_number)

    @staticmethod
    def _extract_temporal_relation(next_chapter_package: Dict[str, Any]) -> str:
        continuity = next_chapter_package.get("continuity", {})
        raw = str(continuity.get("temporal_relation_to_previous_chapter", "") or "")
        return raw.strip().lower()

    @staticmethod
    def _build_package_tokens(next_chapter_package: Dict[str, Any]) -> set[str]:
        token_source: List[str] = []

        chapter_meta = next_chapter_package.get("chapter_meta", {})
        token_source.extend(
            [
                str(chapter_meta.get("chapter_label", "")),
                str(chapter_meta.get("chapter_purpose", "")),
            ]
        )

        start_state = next_chapter_package.get("start_state", {})
        token_source.extend(
            [
                str(start_state.get("detective_working_theory", "")),
                str(start_state.get("current_suspicion_order", "")),
                str(start_state.get("key_active_misconception", "")),
            ]
        )

        end_state = next_chapter_package.get("end_state", {})
        token_source.extend(
            [
                str(end_state.get("detective_updated_working_theory", "")),
                str(end_state.get("suspicion_shift", "")),
                str(end_state.get("newly_understood", "")),
                str(end_state.get("chapter_hook", "")),
            ]
        )

        story_constraints = next_chapter_package.get("story_constraints", {})
        token_source.extend(
            [
                str(story_constraints.get("culprit", "")),
                str(story_constraints.get("detective_name", "")),
                str(story_constraints.get("victim_name", "")),
                str(story_constraints.get("hidden_premise", "")),
                str(story_constraints.get("final_proof", "")),
            ]
        )

        for scene in next_chapter_package.get("scene_plan", []):
            if not isinstance(scene, dict):
                continue
            token_source.extend(
                [
                    str(scene.get("time_and_location", "")),
                    str(scene.get("scene_summary", "")),
                    str(scene.get("detective_takeaway", "")),
                    str(scene.get("reader_facing_effect", "")),
                ]
            )

        for clue in next_chapter_package.get("revealed_clues", []):
            if not isinstance(clue, dict):
                continue
            token_source.extend(
                [
                    str(clue.get("clue_label", "")),
                    str(clue.get("clue_description", "")),
                    str(clue.get("immediate_interpretation", "")),
                    str(clue.get("real_significance", "")),
                ]
            )

        return DetailTripleStore._tokenize("\n".join(token_source))

    @staticmethod
    def _score_record(
        record: Dict[str, Any],
        *,
        next_chapter_number: int | None,
        temporal_relation: str,
        package_tokens: set[str],
    ) -> float:
        chapter = DetailTripleStore._to_int(record.get("chapter"))
        chapter_distance = DetailTripleStore._chapter_distance(chapter, next_chapter_number)

        continuity_window = str(record.get("continuity_window", "same_day") or "same_day").strip().lower()
        temporal_score = DetailTripleStore._temporal_score(
            continuity_window=continuity_window,
            chapter_distance=chapter_distance,
            temporal_relation=temporal_relation,
        )

        record_text = " ".join(
            [
                str(record.get("subject", "")),
                str(record.get("predicate", "")),
                str(record.get("object", "")),
                str(record.get("evidence_snippet", "")),
            ]
        )
        record_tokens = DetailTripleStore._tokenize(record_text)
        overlap_score = 0.0
        if record_tokens and package_tokens:
            overlap = len(record_tokens & package_tokens)
            overlap_score = overlap / len(record_tokens)

        # Temporal relevance is primary; package lexical overlap nudges ties/usefulness.
        return (0.75 * temporal_score) + (0.25 * overlap_score)

    @staticmethod
    def _temporal_score(
        *,
        continuity_window: str,
        chapter_distance: int,
        temporal_relation: str,
    ) -> float:
        half_life_map = {
            "scene": 0.35,
            "same_day": 1.0,
            "multi_day": 3.0,
            "long_term": 8.0,
        }
        half_life = half_life_map.get(continuity_window, 1.0)
        distance_decay = math.exp(-chapter_distance / half_life)

        relation_multipliers = {
            "immediate_continuation": {
                "scene": 1.45,
                "same_day": 1.25,
                "multi_day": 0.9,
                "long_term": 0.8,
            },
            "later_same_day": {
                "scene": 0.75,
                "same_day": 1.35,
                "multi_day": 1.0,
                "long_term": 0.85,
            },
            "next_day": {
                "scene": 0.2,
                "same_day": 0.8,
                "multi_day": 1.2,
                "long_term": 1.0,
            },
            "multi_day_gap": {
                "scene": 0.1,
                "same_day": 0.35,
                "multi_day": 1.35,
                "long_term": 1.2,
            },
            "flashback": {
                "scene": 0.6,
                "same_day": 0.9,
                "multi_day": 1.1,
                "long_term": 1.2,
            },
            "parallel_timeline": {
                "scene": 1.2,
                "same_day": 1.0,
                "multi_day": 0.8,
                "long_term": 0.8,
            },
        }
        relation_window_map = relation_multipliers.get(temporal_relation, {})
        relation_multiplier = relation_window_map.get(continuity_window, 1.0)

        return distance_decay * relation_multiplier

    @staticmethod
    def _chapter_distance(chapter: int | None, next_chapter_number: int | None) -> int:
        if chapter is None or next_chapter_number is None:
            return 99
        return max(0, next_chapter_number - chapter)

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        if not text:
            return set()

        tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
        return {token for token in tokens if len(token) >= 3}

    @staticmethod
    def _to_int(value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None


def triples_to_records(
    triples: List[DetailTriple],
    chapter_number: int | None,
    chapter_text_hash: str = "",
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for triple in triples:
        records.append(
            {
                "subject": triple.subject,
                "predicate": triple.predicate,
                "object": triple.object,
                "chapter": chapter_number,
                "chapter_text_hash": chapter_text_hash,
                "evidence_snippet": triple.evidence_snippet,
                "fact_type": triple.fact_type,
                "subject_type": triple.subject_type,
                "continuity_window": triple.continuity_window,
            }
        )

    return records