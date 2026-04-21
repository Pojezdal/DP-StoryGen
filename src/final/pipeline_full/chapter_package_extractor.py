from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

from final.utils.serialization import StoryDirectory


SECTION_HEADER_RE = re.compile(r"(?m)^#*\s*\**(\d+)\.\s+([A-Z][A-Z0-9\s/\-&()]+)\**\s*$")
CHAPTER_HEADER_RE = re.compile(
    r"(?m)^###\s*CHAPTER\s+(?P<number>\d+)\s*(?:(?:[:\-–—]\s*|\s+)(?P<label>.+?)\s*)?$"
)

SCENE_FIELD_LABELS = [
    "Scene ID",
    "Scene type",
    "Time and location",
    "Scene summary",
    "Detective takeaway",
    "Reader-facing effect",
]

CLUE_FIELD_LABELS = [
    "Clue ID",
    "CL-ID",
    "Clue label",
    "Label",
    "Clue description",
    "Description",
    "How it appears",
    "First discoverable form",
    "Discoverable form",
    "Scene of first appearance",
    "Scene",
    "Reveal mode",
    "Mode",
    "Surface weight at time of reveal",
    "Surface weight",
    "Weight",
    "Who notices",
    "Who consciously notices it",
    "Noticed by",
    "Immediate interpretation",
    "Interpretation",
    "Real significance",
    "True",
]

STATE_FIELD_LABELS = [
    "Temporal relation to previous chapter",
    "Detective working theory",
    "Current suspicion order",
    "Key active misconception",
    "Detective updated working theory",
    "Suspicion shift",
    "What is newly understood",
    "What remains wrongly framed",
    "Culprit pressure update",
    "Reader carry-forward impression",
    "Chapter hook",
]

SUSPECT_BRIEF_TITLE_TO_KEY = {
    "wheretheyclaimtobe": "where_they_claim_to_be",
    "whatsomeoneobserved": "what_someone_observed",
    "oddityorinconsistency": "oddity_or_inconsistency",
    "plausiblereasonforsuspicion": "plausible_reason_for_suspicion",
    "whattheyknow": "what_they_know",
    "whattheymistakenlybelieve": "what_they_mistakenly_believe",
    "immediatepostcrimemove": "immediate_post_crime_move",
    "likelyresponseifpressured": "likely_response_if_pressured",
}


@dataclass
class SceneData:
    scene_id: str
    scene_type: str
    time_and_location: str
    scene_summary: str
    detective_takeaway: str
    reader_facing_effect: str


@dataclass
class ClueData:
    clue_id: str
    clue_label: str
    clue_description: str
    how_it_appears: str
    scene: str
    reveal_mode: str
    surface_weight: str
    who_notices: str
    immediate_interpretation: str
    real_significance: str


@dataclass
class ChapterData:
    chapter_number: int
    chapter_label: str
    chapter_purpose: str
    start_state: Dict[str, str]
    scenes: List[SceneData]
    clues: List[ClueData]
    end_state: Dict[str, str]
    
    
def _strip_header_lines(text: str) -> str:
    return re.sub(r"═*", "", text).strip()

def _to_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value

    if hasattr(value, "model_dump"):
        dumped = value.model_dump()
        return dumped if isinstance(dumped, dict) else {}

    if hasattr(value, "dict"):
        dumped = value.dict()
        return dumped if isinstance(dumped, dict) else {}

    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exception:
            print(f"Warning: Failed to parse string as JSON: {exception}")
            return {}
        return parsed if isinstance(parsed, dict) else {}

    if hasattr(value, "__dict__"):
        raw = value.__dict__
        return raw if isinstance(raw, dict) else {}

    return {}


def _normalize_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", key.lower())


def _normalize_actor_name(name: str) -> str:
    # Normalize punctuation/quote variants so actor names match even when
    # one source uses 'Bea' and another uses "Bea" (or smart quotes).
    lowered = (name or "").lower()
    lowered = re.sub(r"[\"'`“”‘’]", "", lowered)
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def _extract_numbered_sections(text: str) -> Dict[int, Dict[str, str]]:
    matches = list(SECTION_HEADER_RE.finditer(text))
    sections: Dict[int, Dict[str, str]] = {}
    for i, match in enumerate(matches):
        section_num = int(match.group(1))
        title = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        sections[section_num] = {"title": title, "body": _strip_header_lines(body)}
    return sections


def _extract_overview_total_chapters(overview_body: str) -> Optional[int]:
    if not overview_body:
        return None

    patterns = [
        # Matches variants like:
        # - **Proposed Total Chapter Count:** 12 Chapters
        # - Total Chapter Count: 10
        # - Planned Total Chapters: 8
        r"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?\s*(?:proposed|planned|target)?\s*total(?:\s+chapter)?\s*(?:count|number|total)?(?:\s+of\s+chapters?)?\s*:\s*(?:\*\*)?\s*(\d+)\b",
        # Matches variants like:
        # - **Total Chapters:** 12
        # - Total Chapters: 9 Chapters
        r"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?\s*total\s+chapters?\s*:\s*(?:\*\*)?\s*(\d+)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, overview_body)
        if match:
            return int(match.group(1))

    # Fallback: look for a line that mentions chapter + total/count/number and contains a number.
    for raw_line in overview_body.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        normalized = _normalize_key(re.sub(r"\d+", "", line))
        if "chapter" not in normalized:
            continue
        if not any(token in normalized for token in ["total", "count", "number"]):
            continue

        match = re.search(r"\b(\d+)\b", line)
        if match:
            return int(match.group(1))

    return None


def _extract_labeled_blocks(text: str, block_start_label_re: re.Pattern[str]) -> List[str]:
    matches = list(block_start_label_re.finditer(text))
    blocks: List[str] = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        blocks.append(text[start:end].strip())
    return blocks


def _parse_labeled_bullets(
    block_text: str,
    *,
    allowed_labels: Optional[List[str]] = None,
) -> Dict[str, str]:
    line_re = re.compile(
        r"^\s*[-*]?\s*(?:\*\*)?([^*:\n]+?)\s*(?:\*\*)?\s*:\s*(?:\*\*)?\s*(.*)$"
    )
    data: Dict[str, str] = {}
    current_key: Optional[str] = None
    allowed_by_normalized: Optional[Dict[str, str]] = None

    if allowed_labels:
        allowed_by_normalized = {_normalize_key(label): label for label in allowed_labels}

    for raw_line in block_text.splitlines():
        line = raw_line.rstrip()
        match = line_re.match(line)
        if match:
            parsed_label = match.group(1).strip()
            label = parsed_label
            if allowed_by_normalized is not None:
                label = allowed_by_normalized.get(_normalize_key(parsed_label), "")
                if not label:
                    if current_key and line.strip():
                        data[current_key] = (data[current_key] + "\n" + line.strip()).strip()
                    continue
            value = match.group(2).strip()
            data[label] = value
            current_key = label
            continue

        if current_key and line.strip():
            data[current_key] = (data[current_key] + "\n" + line.strip()).strip()

    return data


def _parse_inline_markdown_labels(
    block_text: str,
    *,
    allowed_labels: Optional[List[str]] = None,
) -> Dict[str, str]:
    label_re = re.compile(r"(?:\*\*)?([^*:\n|]+?)\s*(?:\*\*)?\s*:\s*(?:\*\*)?")
    raw_matches = list(label_re.finditer(block_text))
    if not raw_matches:
        return {}

    allowed_by_normalized: Optional[Dict[str, str]] = None
    if allowed_labels:
        allowed_by_normalized = {_normalize_key(label): label for label in allowed_labels}

    matches: List[Tuple[re.Match[str], str]] = []
    for match in raw_matches:
        parsed_label = match.group(1).strip()
        label = parsed_label
        if allowed_by_normalized is not None:
            label = allowed_by_normalized.get(_normalize_key(parsed_label), "")
            if not label:
                continue
        matches.append((match, label))

    if not matches:
        return {}

    data: Dict[str, str] = {}
    for i, (match, label) in enumerate(matches):
        start = match.end()
        end = matches[i + 1][0].start() if i + 1 < len(matches) else len(block_text)
        value = block_text[start:end].strip()
        value = value.strip("|").strip()
        value = re.sub(r"^[-*]\s*", "", value).strip()
        data[label] = value

    return data


def _extract_subsection(chapter_block: str, label: str, next_labels: List[str]) -> str:
    start_re = re.compile(rf"(?m)^\s*(?:\*\*)?{re.escape(label)}(?:\*\*)?\s*$")
    start_match = start_re.search(chapter_block)
    if not start_match:
        return ""

    start = start_match.end()
    end = len(chapter_block)

    for next_label in next_labels:
        next_re = re.compile(rf"(?m)^\s*(?:\*\*)?{re.escape(next_label)}(?:\*\*)?\s*$")
        next_match = next_re.search(chapter_block, start)
        if next_match:
            end = min(end, next_match.start())

    return chapter_block[start:end].strip()


def _extract_chapter_blocks(execution_plan_text: str) -> List[Tuple[int, str, str]]:
    headers = list(CHAPTER_HEADER_RE.finditer(execution_plan_text))
    blocks: List[Tuple[int, str, str]] = []

    for i, header in enumerate(headers):
        chapter_number = int(header.group("number"))
        chapter_label = (header.group("label") or "").strip()
        start = header.start()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(execution_plan_text)
        blocks.append((chapter_number, chapter_label, execution_plan_text[start:end].strip()))

    return blocks


def _parse_scene_blocks(scene_list_text: str) -> List[SceneData]:
    scene_start_re = re.compile(r"(?m)^\s*[-*]?\s*(?:\*\*)?Scene ID:(?:\*\*)?\s*C\d+-S\d+\s*$")
    raw_blocks = _extract_labeled_blocks(scene_list_text, scene_start_re)
    scenes: List[SceneData] = []

    for raw_block in raw_blocks:
        fields = _parse_labeled_bullets(raw_block, allowed_labels=SCENE_FIELD_LABELS)
        scenes.append(
            SceneData(
                scene_id=fields.get("Scene ID", ""),
                scene_type=fields.get("Scene type", ""),
                time_and_location=fields.get("Time and location", ""),
                scene_summary=fields.get("Scene summary", ""),
                detective_takeaway=fields.get("Detective takeaway", ""),
                reader_facing_effect=fields.get("Reader-facing effect", ""),
            )
        )

    return scenes


def _parse_clue_blocks(clue_list_text: str) -> List[ClueData]:
    clue_start_re = re.compile(
        r"(?m)^\s*[-*]?\s*(?:\*\*)?(?:Clue ID|CL-ID):(?:\*\*)?\s*[A-Z]+-\d+.*$"
    )
    raw_blocks = _extract_labeled_blocks(clue_list_text, clue_start_re)
    clues: List[ClueData] = []

    for raw_block in raw_blocks:
        fields = _parse_labeled_bullets(raw_block, allowed_labels=CLUE_FIELD_LABELS)
        inline_fields = _parse_inline_markdown_labels(raw_block, allowed_labels=CLUE_FIELD_LABELS)
        for key, value in inline_fields.items():
            if key not in fields or not fields[key] or "|" in fields[key]:
                fields[key] = value

        clue_id_raw = fields.get("Clue ID", fields.get("CL-ID", ""))
        clue_id_match = re.search(r"[A-Z]+-\d+", clue_id_raw)
        clue_id = clue_id_match.group(0) if clue_id_match else clue_id_raw

        clues.append(
            ClueData(
                clue_id=clue_id,
                clue_label=fields.get("Clue label", fields.get("Label", "")),
                clue_description=fields.get(
                    "Clue description",
                    fields.get("Description", ""),
                ),
                how_it_appears=fields.get(
                    "How it appears",
                    fields.get("First discoverable form", fields.get("Discoverable form", "")),
                ),
                scene=fields.get("Scene of first appearance", fields.get("Scene", "")),
                reveal_mode=fields.get("Reveal mode", fields.get("Mode", "")),
                surface_weight=fields.get("Surface weight at time of reveal", fields.get("Surface weight", fields.get("Weight", ""))),
                who_notices=fields.get(
                    "Who notices",
                    fields.get("Who consciously notices it", fields.get("Noticed by", "")),
                ),
                immediate_interpretation=fields.get(
                    "Immediate interpretation", fields.get("Interpretation", "")
                ),
                real_significance=fields.get("Real significance", fields.get("True", "")),
            )
        )

    return clues


def _parse_start_or_end_state(block_text: str) -> Dict[str, str]:
    raw = _parse_labeled_bullets(block_text, allowed_labels=STATE_FIELD_LABELS)
    normalized: Dict[str, str] = {}

    for key, value in raw.items():
        normalized[_normalize_key(key)] = value

    return normalized


def _parse_chapters(section_2_body: str) -> List[ChapterData]:
    chapters: List[ChapterData] = []
    chapter_blocks = _extract_chapter_blocks(section_2_body)

    for chapter_number, chapter_label, chapter_block in chapter_blocks:
        chapter_purpose = _extract_subsection(
            chapter_block,
            "A. CHAPTER PURPOSE",
            [
                "B. START STATE",
                "C. SCENE LIST",
                "D. CLUE / INFORMATION REVEAL LEDGER",
                "E. CHAPTER END STATE",
            ],
        )
        start_state_text = _extract_subsection(
            chapter_block,
            "B. START STATE",
            [
                "C. SCENE LIST",
                "D. CLUE / INFORMATION REVEAL LEDGER",
                "E. CHAPTER END STATE",
            ],
        )
        scene_list_text = _extract_subsection(
            chapter_block,
            "C. SCENE LIST",
            [
                "D. CLUE / INFORMATION REVEAL LEDGER",
                "E. CHAPTER END STATE",
            ],
        )
        clue_list_text = _extract_subsection(
            chapter_block,
            "D. CLUE / INFORMATION REVEAL LEDGER",
            ["E. CHAPTER END STATE"],
        )
        end_state_text = _extract_subsection(chapter_block, "E. CHAPTER END STATE", [])

        chapters.append(
            ChapterData(
                chapter_number=chapter_number,
                chapter_label=chapter_label,
                chapter_purpose=chapter_purpose,
                start_state=_parse_start_or_end_state(start_state_text),
                scenes=_parse_scene_blocks(scene_list_text),
                clues=_parse_clue_blocks(clue_list_text),
                end_state=_parse_start_or_end_state(end_state_text),
            )
        )

    return chapters


def _extract_actor_context(
    story_data: Any,
) -> Tuple[
    List[str],
    Optional[str],
    Optional[str],
    Optional[str],
    Dict[str, Dict[str, Any]],
]:
    story_data_dict = _to_dict(story_data)
    actor_pool = _to_dict(story_data_dict.get("actor_pool", {}))

    suspects_raw = actor_pool.get("suspects", [])
    if not isinstance(suspects_raw, list):
        suspects_raw = []
    suspects = [_to_dict(item) for item in suspects_raw]

    side_characters_raw = actor_pool.get("side_characters", [])
    if not isinstance(side_characters_raw, list):
        side_characters_raw = []
    side_characters = [_to_dict(item) for item in side_characters_raw]

    detective = _to_dict(actor_pool.get("detective", {}))
    side_kick = _to_dict(actor_pool.get("side_kick", {}))
    victim = _to_dict(actor_pool.get("victim", {}))

    actor_names: List[str] = []
    culprit_name: Optional[str] = None
    detective_name: Optional[str] = None
    actor_catalog: Dict[str, Dict[str, Any]] = {}

    def _to_relationship_list(value: Any) -> List[Dict[str, str]]:
        if not isinstance(value, list):
            return []

        rels: List[Dict[str, str]] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            rel_type = str(item.get("type", "")).strip()
            target = str(item.get("target", "")).strip()
            rels.append({"type": rel_type, "target": target})
        return rels

    def _add_actor(raw_actor: Dict[str, Any], role: str, *, culprit_flag: Optional[bool] = None) -> None:
        name_raw = raw_actor.get("name")
        if not name_raw:
            return
        name = str(name_raw)
        actor_names.append(name)

        entry = actor_catalog.get(name, {"name": name, "roles": []})
        if role not in entry["roles"]:
            entry["roles"].append(role)

        occupation = raw_actor.get("occupation")
        if isinstance(occupation, str) and occupation.strip():
            entry["occupation"] = occupation.strip()

        description = raw_actor.get("description")
        if isinstance(description, str) and description.strip():
            entry["description"] = description.strip()

        traits = raw_actor.get("character_traits")
        if isinstance(traits, list):
            trait_labels: list[str] = []
            trait_facets: list[Dict[str, str]] = []
            for t in traits:
                if isinstance(t, dict):
                    trait_name = str(t.get("trait", "")).strip()
                    if trait_name:
                        trait_labels.append(trait_name)

                    facet: Dict[str, str] = {}
                    for key in ("trait", "manifestation", "vulnerability"):
                        value = t.get(key)
                        if isinstance(value, str) and value.strip():
                            facet[key] = value.strip()
                    if facet:
                        trait_facets.append(facet)
                else:
                    trait_text = str(t).strip()
                    if trait_text:
                        trait_labels.append(trait_text)

            if trait_labels:
                entry["character_traits"] = trait_labels
            if trait_facets:
                entry["trait_facets"] = trait_facets

        rels = _to_relationship_list(raw_actor.get("relationships"))
        if rels:
            entry["relationships"] = rels

        if culprit_flag is not None:
            entry["culprit"] = bool(culprit_flag)

        actor_catalog[name] = entry

    if detective.get("name"):
        detective_name = str(detective.get("name"))
    _add_actor(detective, "detective")

    _add_actor(victim, "victim")
    _add_actor(side_kick, "side_kick")

    for side_character in side_characters:
        _add_actor(side_character, "side_character")

    for suspect in suspects:
        name = suspect.get("name")
        _add_actor(suspect, "suspect", culprit_flag=bool(suspect.get("culprit") is True))
        if suspect.get("culprit") is True and name:
            culprit_name = str(name)

    if culprit_name is None:
        top_level_culprit = story_data_dict.get("culprit_name")
        if isinstance(top_level_culprit, str) and top_level_culprit.strip():
            culprit_name = top_level_culprit.strip()

    if culprit_name and culprit_name in actor_catalog:
        actor_catalog[culprit_name]["culprit"] = True

    for entry in actor_catalog.values():
        roles = entry.get("roles")
        if isinstance(roles, list):
            entry["roles"] = sorted({str(role) for role in roles})

    victim_name = str(victim.get("name")) if victim.get("name") else None
    return culprit_name, victim_name, detective_name, actor_catalog


def _extract_suspect_briefs_profiles(suspect_briefs_text: Optional[str]) -> Dict[str, Dict[str, str]]:
    if not suspect_briefs_text:
        return {}

    profile_header_re = re.compile(r"(?m)^###\s*\*\*([^*]+)\*\*\s*$")
    section_header_re = re.compile(r"(?m)^\s*([1-8])\.\s+(.+?)\s*$")
    matches = list(profile_header_re.finditer(suspect_briefs_text))
    profiles: Dict[str, Dict[str, str]] = {}

    for i, match in enumerate(matches):
        raw_name = match.group(1).strip()
        name = re.sub(r"\s*\([^)]*\)\s*$", "", raw_name).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(suspect_briefs_text)
        block = suspect_briefs_text[start:end]

        sections = list(section_header_re.finditer(block))
        profile_data: Dict[str, str] = {
            "where_they_claim_to_be": "",
            "what_someone_observed": "",
            "oddity_or_inconsistency": "",
            "plausible_reason_for_suspicion": "",
            "what_they_know": "",
            "what_they_mistakenly_believe": "",
            "immediate_post_crime_move": "",
            "likely_response_if_pressured": "",
        }

        for section_index, section_match in enumerate(sections):
            section_title = _normalize_key(section_match.group(2))
            key = SUSPECT_BRIEF_TITLE_TO_KEY.get(section_title)
            if not key:
                continue

            section_start = section_match.end()
            section_end = (
                sections[section_index + 1].start()
                if section_index + 1 < len(sections)
                else len(block)
            )
            section_body = block[section_start:section_end].strip()
            profile_data[key] = section_body

        profiles[name] = profile_data

    return profiles


def _add_suspect_briefs_to_actor_catalog(
    actor_catalog: Dict[str, Dict[str, Any]],
    suspect_briefs_profiles: Dict[str, Dict[str, str]],
) -> Dict[str, Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    normalized_profiles: Dict[str, Dict[str, str]] = {}

    for brief_name, profile in suspect_briefs_profiles.items():
        normalized_name = _normalize_actor_name(brief_name)
        if normalized_name and normalized_name not in normalized_profiles:
            normalized_profiles[normalized_name] = profile

    for name in sorted(actor_catalog.keys()):
        merged_entry: Dict[str, Any] = dict(actor_catalog[name])

        profile = suspect_briefs_profiles.get(name)
        if profile is None:
            profile = normalized_profiles.get(_normalize_actor_name(name))

        if profile is not None:
            merged_entry["suspect_brief"] = dict(profile)
        merged[name] = merged_entry
        
    return merged


def _extract_crime_constraints(crime_narrative_text: Optional[str]) -> Dict[str, str]:
    if not crime_narrative_text:
        return {}

    sections: Dict[str, str] = {}
    for title in [
        "1. MOTIVE & DECISION",
        "2. ESCAPE STRATEGY",
        "3. PREPARATION",
        "4. EXECUTION",
        "5. COVER-UP",
        "6. COMPLICATIONS",
        "7. EVIDENCE LANDSCAPE",
    ]:
        match = re.search(
            rf"(?ms)^\s*###\s*{re.escape(title)}\s*$\s*(.*?)(?=^\s*###\s*\d+\.\s|\Z)",
            crime_narrative_text,
        )
        if match:
            sections[title] = match.group(1).strip()

    return {
        "motive_and_decision": sections.get("1. MOTIVE & DECISION", ""),
        "escape_strategy": sections.get("2. ESCAPE STRATEGY", ""),
        "preparation": sections.get("3. PREPARATION", ""),
        "execution": sections.get("4. EXECUTION", ""),
        "cover_up": sections.get("5. COVER-UP", ""),
        "complications": sections.get("6. COMPLICATIONS", ""),
        "evidence_landscape": sections.get("7. EVIDENCE LANDSCAPE", ""),
    }


def _extract_architecture_constraints(architecture_text: Optional[str]) -> Dict[str, str]:
    if not architecture_text:
        return {}

    sections = _extract_numbered_sections(architecture_text)
    return {
        "story_outline_section": sections.get(1, {}).get("body", ""),
        "beat_map_section": sections.get(2, {}).get("body", ""),
        "breakthrough_design_section": sections.get(3, {}).get("body", ""),
    }


def _coerce_clue_graph_dict(clue_graph: Any) -> Dict[str, Any]:
    if clue_graph is None:
        return {}

    if isinstance(clue_graph, dict):
        return clue_graph

    if hasattr(clue_graph, "model_dump"):
        dumped = clue_graph.model_dump()
        if isinstance(dumped, dict):
            return dumped

    if isinstance(clue_graph, str):
        if not clue_graph.strip():
            return {}
        try:
            parsed = json.loads(clue_graph)
        except json.JSONDecodeError as exception:
            print(f"Warning: Failed to parse clue_graph string as JSON: {exception}")
            return {}
        return parsed if isinstance(parsed, dict) else {}

    return {}


def _extract_clue_graph_context(clue_graph: Any) -> Dict[str, Any]:
    graph = _coerce_clue_graph_dict(clue_graph)
    if not graph:
        return {
            "enabled": False,
            "total_nodes": 0,
            "total_edges": 0,
            "total_suspect_branches": 0,
            "proof_chain_node_ids": [],
            "final_solution_node_ids": [],
            "culprit_branch_suspect": "",
            "dead_end_branch_suspects": [],
            "open_branch_suspects": [],
        }

    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    branches = graph.get("suspect_branches", [])
    if not isinstance(nodes, list):
        nodes = []
    if not isinstance(edges, list):
        edges = []
    if not isinstance(branches, list):
        branches = []

    culprit_branch_suspect = ""
    dead_end_branch_suspects: List[str] = []
    open_branch_suspects: List[str] = []

    for branch in branches:
        if not isinstance(branch, dict):
            continue
        suspect_name = str(branch.get("suspect_name", "")).strip()
        outcome = str(branch.get("outcome", "")).strip()

        if outcome == "confirmed_culprit" and suspect_name:
            culprit_branch_suspect = suspect_name
        elif outcome == "dead_end" and suspect_name:
            dead_end_branch_suspects.append(suspect_name)
        elif outcome == "open" and suspect_name:
            open_branch_suspects.append(suspect_name)

    proof_chain_node_ids = [
        str(node_id)
        for node_id in graph.get("primary_proof_chain_node_ids", [])
        if str(node_id).strip()
    ]
    final_solution_node_ids = [
        str(node_id)
        for node_id in graph.get("final_solution_node_ids", [])
        if str(node_id).strip()
    ]

    return {
        "enabled": True,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "total_suspect_branches": len(branches),
        "proof_chain_node_ids": proof_chain_node_ids,
        "final_solution_node_ids": final_solution_node_ids,
        "culprit_branch_suspect": culprit_branch_suspect,
        "dead_end_branch_suspects": dead_end_branch_suspects,
        "open_branch_suspects": open_branch_suspects,
    }


def _unique_non_empty(values: List[str]) -> List[str]:
    seen: set[str] = set()
    unique_values: List[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_values.append(normalized)
    return unique_values


def _build_clue_timeline_maps(
    chapters: List[ChapterData],
) -> Tuple[Dict[int, List[Dict[str, Any]]], Dict[int, List[Dict[str, Any]]], Dict[int, List[Dict[str, Any]]]]:
    revealed_by_chapter: Dict[int, List[Dict[str, Any]]] = {}

    for chapter in chapters:
        chapter_clues = [
            asdict(clue)
            for clue in chapter.clues
            if clue.clue_id.strip()
        ]
        for clue in chapter_clues:
            clue["chapter_number"] = chapter.chapter_number
        revealed_by_chapter[chapter.chapter_number] = chapter_clues

    previously_revealed_by_chapter: Dict[int, List[Dict[str, Any]]] = {}
    previously_revealed: List[Dict[str, Any]] = []
    for chapter in chapters:
        chapter_number = chapter.chapter_number
        previously_revealed_by_chapter[chapter_number] = list(previously_revealed)
        previously_revealed.extend(revealed_by_chapter.get(chapter_number, []))

    future_revealed_by_chapter: Dict[int, List[Dict[str, Any]]] = {}
    future_revealed: List[Dict[str, Any]] = []
    for chapter in reversed(chapters):
        chapter_number = chapter.chapter_number
        future_revealed_by_chapter[chapter_number] = list(future_revealed)
        future_revealed = revealed_by_chapter.get(chapter_number, []) + future_revealed

    return revealed_by_chapter, previously_revealed_by_chapter, future_revealed_by_chapter


def _to_stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _is_changed(latest: Any, new_value: Any) -> bool:
    if latest is None:
        return True
    return _to_stable_json(latest) != _to_stable_json(new_value)


def _build_validation_report(
    chapters: List[ChapterData],
    declared_overview_total: Optional[int],
) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []
    parsed_total = len(chapters)

    if declared_overview_total is not None and declared_overview_total != parsed_total:
        warnings.append(
            "Overview chapter count mismatch: "
            f"declared={declared_overview_total}, parsed={parsed_total}. "
            "Using parsed chapter count as canonical."
        )

    clue_counts: Dict[str, int] = {}

    for chapter in chapters:
        if not chapter.chapter_label:
            warnings.append(f"Chapter {chapter.chapter_number}: missing chapter label in header.")

        if not chapter.chapter_purpose:
            warnings.append(f"Chapter {chapter.chapter_number}: missing chapter purpose.")

        if len(chapter.scenes) == 0:
            errors.append(f"Chapter {chapter.chapter_number}: no scenes parsed.")

        for scene in chapter.scenes:
            if not scene.scene_id:
                warnings.append(f"Chapter {chapter.chapter_number}: scene missing scene_id.")
            if not scene.scene_summary:
                warnings.append(
                    f"Chapter {chapter.chapter_number}: scene {scene.scene_id} missing summary."
                )

        if "chapterhook" not in chapter.end_state or not chapter.end_state.get("chapterhook"):
            warnings.append(f"Chapter {chapter.chapter_number}: missing chapter hook.")

        for clue in chapter.clues:
            if clue.clue_id:
                clue_counts[clue.clue_id] = clue_counts.get(clue.clue_id, 0) + 1

    duplicates = [cid for cid, cnt in clue_counts.items() if cnt > 1]
    if duplicates:
        warnings.append(
            "Duplicate clue IDs detected across chapters: " + ", ".join(sorted(duplicates))
        )

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "declared_overview_chapters": declared_overview_total,
            "parsed_chapters": parsed_total,
            "total_scenes": sum(len(ch.scenes) for ch in chapters),
            "total_clues": sum(len(ch.clues) for ch in chapters),
        },
    }


def extract_chapter_packages(
    *,
    story_data: Any,
    chapter_outline: str,
    crime_narrative: str,
    suspect_briefs: str,
    architecture: str,
    clue_graph: Any = None,
) -> Dict[str, Any]:
    if not chapter_outline:
        raise ValueError("chapter_outline is required")

    chapter_outline_text = chapter_outline
    crime_narrative_text = crime_narrative or ""
    suspect_briefs_text = suspect_briefs or ""
    architecture_text = architecture or ""

    sections = _extract_numbered_sections(chapter_outline_text)
    overview_body = sections.get(1, {}).get("body", "")
    execution_body = sections.get(2, {}).get("body", "")
    global_distribution_body = sections.get(3, {}).get("body", "")
    pacing_body = sections.get(4, {}).get("body", "")

    if not execution_body:
        raise ValueError("Could not find section 2 (chapter-by-chapter execution plan).")

    chapters = _parse_chapters(execution_body)
    parsed_total = len(chapters)

    declared_overview_total = _extract_overview_total_chapters(overview_body)

    culprit_from_actor, victim_name, detective_name, actor_catalog = _extract_actor_context(story_data)
    suspect_briefs_profiles = _extract_suspect_briefs_profiles(suspect_briefs_text)
    actor_catalog = _add_suspect_briefs_to_actor_catalog(actor_catalog, suspect_briefs_profiles)

    crime_constraints = _extract_crime_constraints(crime_narrative_text)
    architecture_constraints = _extract_architecture_constraints(architecture_text)
    clue_graph_context = _extract_clue_graph_context(clue_graph)

    hidden_premise_text = (
        architecture_constraints.get("story_outline_section", "")
        or crime_constraints.get("evidence_landscape", "")
    )
    final_proof_text = architecture_constraints.get("breakthrough_design_section", "")
    proof_chain_node_ids = clue_graph_context.get("proof_chain_node_ids", [])
    if proof_chain_node_ids:
        final_proof_text = (
            final_proof_text.strip() + "\n\n" if final_proof_text.strip() else ""
        ) + "Clue graph proof-chain nodes: " + " -> ".join(proof_chain_node_ids)

    chapter_packages: List[Dict[str, Any]] = []
    previous_hook = ""
    previous_wrongly_framed = ""

    (
        all_clues,
        previously_revealed_map,
        future_revealed_map,
    ) = _build_clue_timeline_maps(chapters)

    for chapter in chapters:
        suspicion_text = chapter.start_state.get("currentsuspicionorder", "")
        end_hook = chapter.end_state.get("chapterhook", "")
        end_wrongly_framed = chapter.end_state.get("whatremainswronglyframed", "")

        chapter_number = chapter.chapter_number
        revealed_clues = all_clues.get(chapter_number, [])
        previously_revealed_clues = previously_revealed_map.get(chapter_number, [])
        forbidden_clues = future_revealed_map.get(chapter_number, [])

        package = {
            "chapter_meta": {
                "chapter_number": chapter_number,
                "chapter_label": chapter.chapter_label,
                "chapter_purpose": chapter.chapter_purpose,
            },
            "start_state": {
                "detective_working_theory": chapter.start_state.get("detectiveworkingtheory", ""),
                "current_suspicion_order": suspicion_text,
                "key_active_misconception": chapter.start_state.get("keyactivemisconception", ""),
            },
            "scene_plan": [asdict(scene) for scene in chapter.scenes],
            "revealed_clues": revealed_clues,
            "previously_revealed_clues": previously_revealed_clues,
            "forbidden_clues": forbidden_clues,
            "end_state": {
                "detective_updated_working_theory": chapter.end_state.get(
                    "detectiveupdatedworkingtheory", ""
                ),
                "suspicion_shift": chapter.end_state.get("suspicionshift", ""),
                "newly_understood": chapter.end_state.get("whatisnewlyunderstood", ""),
                "remains_wrongly_framed": end_wrongly_framed,
                "culprit_pressure_update": chapter.end_state.get("culpritpressureupdate", ""),
                "reader_carry_forward_impression": chapter.end_state.get(
                    "readercarryforwardimpression", ""
                ),
                "chapter_hook": end_hook,
            },
            "continuity": {
                "temporal_relation_to_previous_chapter": chapter.start_state.get(
                    "temporalrelationtopreviouschapter",
                    "",
                ),
                "prior_chapter_hook": previous_hook,
                "prior_wrongly_framed": previous_wrongly_framed
            },
            "story_constraints": {
                "culprit": culprit_from_actor,
                "detective_name": detective_name,
                "victim_name": victim_name,
                "hidden_premise": hidden_premise_text,
                "final_proof": final_proof_text,
                "motive_and_decision": crime_constraints.get("motive_and_decision", ""),
                "execution_truth": crime_constraints.get("execution", ""),
                "cover_up_truth": crime_constraints.get("cover_up", ""),
                "suspect_briefs_reference": suspect_briefs_text,
            },
        }

        chapter_packages.append(package)
        previous_hook = end_hook
        previous_wrongly_framed = end_wrongly_framed

    validation = _build_validation_report(chapters, declared_overview_total)

    return {
        "overview": {
            "total_chapters": parsed_total,
            "declared_total_chapters": declared_overview_total,
            "overview_text": overview_body,
            "global_clue_distribution": global_distribution_body,
            "pacing_notes": pacing_body,
            "story_outline": architecture_constraints.get("story_outline_section", ""),
            "architecture_beat_map": architecture_constraints.get("beat_map_section", ""),
            "breakthrough_design": architecture_constraints.get("breakthrough_design_section", ""),
            "clue_graph_context": clue_graph_context,
        },
        "actors": actor_catalog,
        "chapter_packages": chapter_packages,
        "validation": validation,
    }


def save_chapter_packages(
    story_directory: StoryDirectory,
    story_data: Any,
    chapter_outline: str,
    crime_narrative: str,
    suspect_briefs: str,
    architecture: str,
    clue_graph: Any = None,
) -> Dict[str, Any]:
    result = extract_chapter_packages(
        story_data=story_data,
        chapter_outline=chapter_outline,
        crime_narrative=crime_narrative,
        suspect_briefs=suspect_briefs,
        architecture=architecture,
        clue_graph=clue_graph,
    )

    latest_package, _ = story_directory.load_stage("chapter_package_extraction")
    new_validation = result.get("validation", {})

    if _is_changed(latest_package, result):
        story_directory.save_stage("chapter_package_extraction", result)
        story_directory.save_stage("chapter_package_validation", new_validation)
        print("Saved new chapter_package_extraction stage (content changed).")
    else:
        print("Skipped saving chapter_package_extraction (no changes detected).")
  
    return result
