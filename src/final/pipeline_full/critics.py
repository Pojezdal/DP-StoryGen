import re
import os
from pathlib import Path
from typing import Any

from final.utils.prompt_builder import build_prompt
from final.utils.serialization import StoryDirectory
from final.llm.llm import LLM, GenerationParams, GenerationResult
from .schemas.story_data import StoryData

_PROMPT_DIR = Path(__file__).parent / "prompts" / "critics"
_INCLUDE_THOUGHTS = True
_DEFAULT_THINKING_BUDGET = 24576 # using maximum thinking budget for all stages in the pipeline, can be adjusted as needed

DEFAULT_INVESTIGATION_BEATS_CRITIC_CONFIGS: list[dict[str, str]] = [
    {
        "persona_name": "The Fair-Play Advocate",
        "persona_description": (
            "A Knox/Van Dine rules purist and veteran mystery reviewer who "
            "insists that the reader must have a fair chance to solve the "
            "mystery before the detective does. You believe the highest "
            "achievement of a mystery is an ending that makes the reader "
            'say "Of course! I should have seen it!" You have zero '
            "tolerance for hidden evidence, retroactive logic, invisible "
            "discoveries, or last-minute explanation patches."
        ),
        "criterion_name": "Clue Integrity, Discoverability & Fair Play",
        "criterion_description": (
            "Evaluate the investigation beats output for fair-play mystery design. "
            "FOCUS AREAS:\n"
            "- SURFACE STAGE FAIRNESS: Does the CASE SURFACE MODEL and FALSE THEORY LADDER "
            "create plausible early interpretations without accidentally identifying the true "
            "culprit too strongly too soon?\n"
            "- FALSE THEORY VALIDITY: Are the false theories coherent mini-solutions "
            "(apparent motive + means + opportunity), or are they weak, artificial, or "
            "obviously doomed?\n"
            "- DISCOVERABILITY: Are all important clues that matter later introduced in a "
            "discoverable form before they are used in the later investigation beats or final proof?\n"
            "- NO HIDDEN SOLUTION LOGIC: Does the final solution rely on any fact, inference, "
            "or access path that was not previously established?\n"
            "- EVIDENCE DISTRIBUTION: Is solution-relevant evidence spread across the pipeline "
            "(surface → agenda reactions → beats), rather than being dumped only at the end?\n"
            "- ACCESS PATH FAIRNESS: If private information, hidden objects, or sensitive records "
            "matter, is there a plausible way investigators could obtain them stated in the beats?\n"
            "- CLUE REINTERPRETATION QUALITY: Do earlier clues change meaning in a satisfying and "
            "traceable way, rather than simply being overwritten by the final explanation?\n"
            "- KNOWLEDGE BOUNDARIES: Do suspects and culprit only react to information they could "
            "plausibly know at that point in the investigation? Flag omniscient reactions.\n"
            "- FULL PICTURE: Are all important clues revealed? Do they provide enough information "
            "to explain key point of the crime?\n\n" 
            "WHEN CRITIQUING:\n"
            "- Identify specific clues, theories, or beats that violate fair play.\n"
            "- Point out where the reader would feel cheated, underinformed, or prematurely certain.\n"
            "- Suggest concrete fixes with downstream-first priority; escalate to upstream stage changes only for major root-cause defects that cannot be repaired downstream."
        ),
    },
    {
        "persona_name": "The Twist Architect",
        "persona_description": (
            "A thriller editor obsessed with misdirection, dramatic pacing, "
            "and the art of surprise. You believe a great mystery is a magic "
            "trick: the audience should be looking directly at the answer "
            "without recognizing it, and each investigative turn should "
            "intensify pressure while narrowing possibility."
        ),
        "criterion_name": "Misdirection, Theory Progression & Investigative Pacing",
        "criterion_description": (
            "Evaluate the dramatic architecture of the investigation beats output. "
            "FOCUS AREAS:\n"
            "- STRONG OPENING MODEL: Does the surface stage create a compelling first reading "
            "of the case, with a clear apparent explanation and a meaningful anomaly?\n"
            "- FALSE THEORY LADDER STRENGTH: Do the working theories escalate in depth and sophistication, "
            "or do they feel repetitive, shallow, or interchangeable?\n"
            "- SUSPICION TRAJECTORY: Is there a clear and convincing progression from early suspect(s) "
            "to deeper wrong suspect(s) to true culprit, with actual theory shifts rather than random suspicion bouncing?\n"
            "- RED HERRING QUALITY: Are non-culprit agendas and secrets strong enough to temporarily support "
            "coherent alternative solutions, or do they just create generic suspicious noise?\n"
            "- COMPLICATIONS, NOT JUST ACCUMULATION: Do the investigation beats create real reversals, setbacks, "
            "or interpretive collapses, rather than merely adding more facts?\n"
            "- MIDPOINT OR LATE REVERSAL: Is there a major discovery that meaningfully destabilizes the current case theory?\n"
            "- PAYOFF OF AGENDAS: Do the character-agenda outputs actually influence later beats and theory shifts, "
            "or do they exist as isolated annotations with no dramatic consequence?\n"
            "- ENDGAME CONVERGENCE: Do the final beats accelerate toward the solution cleanly, or does the case meander "
            "too long and then resolve abruptly?\n"
            "- REVEAL SATISFACTION: Does the hidden premise / final proof genuinely reframe earlier material in a surprising "
            "but inevitable way?\n\n"
            "WHEN CRITIQUING:\n"
            "- Point to dead zones, redundant beats, weak false theories, or unearned reveals.\n"
            "- Suggest where to strengthen, merge, cut, or reorder theories/beats.\n"
            "- Focus on pacing of information and the quality of misdirection, not prose style."
        ),
    },
    {
        "persona_name": "The Character Psychologist",
        "persona_description": (
            "A behavioral analyst and literary critic who evaluates whether "
            "fictional characters behave like real human beings under stress. "
            "You are highly sensitive to characters acting only to satisfy plot "
            "mechanics. You believe the best mysteries work because every lie, "
            "panic, delay, and overreaction emerges from a believable agenda."
        ),
        "criterion_name": "Behavioral Realism, Agenda Logic & Reactive Plausibility",
        "criterion_description": (
            "Evaluate whether the investigation beats output preserves realistic human behavior. "
            "FOCUS AREAS:\n"
            "- AGENDA AUTHENTICITY: Do all major suspects (not only the culprit) have believable ongoing "
            "investigation-phase goals, fears, and self-protective behaviors?\n"
            "- NON-CULPRIT ACTIVITY: Are non-culprit suspects active in ways that make sense for their own secrets "
            "(protecting reputation, hiding affairs, avoiding exposure, moving unrelated evidence, pressuring witnesses, etc.), "
            "rather than existing only as clue dispensers?\n"
            "- SELECTIVE EVASION: In interviews and interactions, do suspects behave realistically—cooperative on neutral facts, "
            "evasive only where their actual secret is threatened?\n"
            "- CULPRIT COUNTERMOVE PLAUSIBILITY: Are the culprit's investigation-phase reactions limited, grounded, and proportional "
            "to what they know, what they fear, and what pressure they feel? Flag over-clever sabotage or omniscient interference.\n"
            "- INFORMATION RESPONSE LOGIC: When new discoveries occur, do characters react in ways consistent with their motives and "
            "awareness, or do they ignore obvious threats they would realistically notice?\n"
            "- MOTIVE-PROPORTION MATCH: Are lies, concealments, and risk-taking proportionate to each character's secret? "
            "Minor embarrassment should not produce extreme criminal behavior unless justified.\n"
            "- DETECTIVE REASONING HUMANITY: Does the detective's breakthrough arise from understanding human behavior, contradictions, "
            "fear, timing, and motive patterns—not solely from a late forensic miracle?\n"
            "- CROSS-STAGE CONSISTENCY: Do the agendas established actually match how characters behave in the later beats, "
            "or do they contradict themselves once the plot advances?\n\n"
            "WHEN CRITIQUING:\n"
            "- Identify characters whose actions feel mechanical, under-motivated, or too convenient.\n"
            "- Suggest how to reframe agendas, reactions, or beat triggers so they emerge from believable psychology.\n"
            "- Prioritize fixing downstream investigation layers first; request upstream changes only when absolutely necessary for major root-cause issues."
        ),
    },
]


_CRITIC_STAGE_ORDER = [
    "surface_level_generation",
    "agendas_generation",
    "investigation_generation",
    "side_stories_generation",
    "crime_generation",
]
_REVISED_PACKAGE_START = "<<<REVISED PACKAGE START>>>"
_REVISED_PACKAGE_END = "<<<REVISED PACKAGE END>>>"
_STAGE_HEADER_RE = re.compile(r"^###\s+STAGE:\s*([a-z_]+)\s*$", re.MULTILINE)


def critique_investigation_package(
    llm: LLM,
    story_directory: StoryDirectory,
    story_data: StoryData,
    crime_narrative: str,
    side_stories: str,
    surface_level: str,
    agendas: str,
    investigation: str,
    run_index: int = -1,
    num_rounds: int = 1,
    critic_configs: list[dict[str, str]] | None = None,
) -> dict[str, str]:
    """Run multi-round critics loop on the investigation package.

    The process is index-addressed and resumable. For a given ``run_index``,
    existing critic/leader/evaluator artifacts are loaded and only missing parts
    are generated. This allows continuing from mid-loop after API failures.

    Special behavior: if ``run_index == -1``, a new run index is automatically
    selected as the next available index based on existing critics artifacts.
    """
    if run_index == -1:
        run_index = _next_critics_run_index(story_directory)
    elif run_index < -1:
        raise ValueError("run_index must be >= -1")

    if num_rounds <= 0:
        raise ValueError("num_rounds must be >= 1")

    if critic_configs is None:
        critic_configs = DEFAULT_INVESTIGATION_BEATS_CRITIC_CONFIGS

    story_data_text = story_data if isinstance(story_data, str) else story_data.model_dump_json(indent=2)
    run_prefix = f"critics_{run_index:02d}"
    initial_package = {
        "surface_level_generation": surface_level,
        "agendas_generation": agendas,
        "investigation_generation": investigation,
        "side_stories_generation": side_stories,
        "crime_generation": crime_narrative,
    }

    current_package = dict(initial_package)
    round_packages: list[dict[str, str]] = []

    for round_num in range(1, num_rounds + 1):
        leader_name = f"{run_prefix}_r{round_num:02d}_leader"
        _, leader_cached = story_directory.load_stage(leader_name)

        if leader_cached is None:
            critiques: list[str] = []
            for config in critic_configs:
                critic_slug = _slugify(config["persona_name"])
                critic_name = (
                    f"{run_prefix}_r{round_num:02d}_critic_{critic_slug}"
                )
                _, critique_cached = story_directory.load_stage(critic_name)
                if critique_cached is None:
                    critique_cached = _call_critic_persona(
                        llm=llm,
                        config=config,
                        story_data_text=story_data_text,
                        current_package=current_package,
                    )
                    story_directory.save_stage_llm(
                        stage=critic_name,
                        model=llm.model_id,
                        prompt=critique_cached["prompt"],
                        system_instruction=critique_cached["system_instruction"],
                        generation_params=critique_cached["generation_params"],
                        generation_result=critique_cached["generation_result"],
                    )
                    critique_text = critique_cached["generation_result"].output
                    print(f"Completed critique from {config['persona_name']} for round {round_num}.")
                else:
                    critique_text = critique_cached
                    print(f"Loaded existing critique from {config['persona_name']} for round {round_num} from cache.")

                critiques.append(critique_text)

            leader_cached = _call_leader(
                llm=llm,
                critic_configs=critic_configs,
                critiques=critiques,
                story_data_text=story_data_text,
                current_package=current_package,
            )
            story_directory.save_stage_llm(
                stage=leader_name,
                model=llm.model_id,
                prompt=leader_cached["prompt"],
                system_instruction=leader_cached["system_instruction"],
                generation_params=leader_cached["generation_params"],
                generation_result=leader_cached["generation_result"],
            )
            leader_text = leader_cached["generation_result"].output
            print(f"Completed critique round {round_num} with new leader generation.")
        else:
            leader_text = leader_cached
            print(f"Loaded existing leader for critique round {round_num} from cache.")

        current_package = _parse_revised_package(leader_text, current_package)
        round_packages.append(dict(current_package))

    if len(round_packages) == 1:
        final_package = round_packages[0]
        print("Only one critique round configured; skipping final evaluation step and using that round's leader output as final package.")
    else:
        evaluator_name = f"{run_prefix}_evaluator"
        _, evaluator_cached = story_directory.load_stage(evaluator_name)

        if evaluator_cached is None:
            evaluator_call = _call_evaluator(
                llm=llm,
                story_data_text=story_data_text,
                crime_narrative=crime_narrative,
                side_stories=side_stories,
                versions=[initial_package] + round_packages,
            )
            story_directory.save_stage_llm(
                stage=evaluator_name,
                model=llm.model_id,
                prompt=evaluator_call["prompt"],
                system_instruction=evaluator_call["system_instruction"],
                generation_params=evaluator_call["generation_params"],
                generation_result=evaluator_call["generation_result"],
            )
            evaluator_text = evaluator_call["generation_result"].output
            print("Completed final evaluation of all critique rounds with new evaluator generation.")
        else:
            evaluator_text = evaluator_cached
            print("Loaded existing final evaluation of all critique rounds from cache.")

        final_package = _parse_revised_package(evaluator_text, round_packages[-1])

    for stage_name, stage_text in final_package.items():
        story_directory.save_plain(f"{run_prefix}_final_{stage_name}.txt", stage_text)

    return final_package


def _call_critic_persona(
    llm: LLM,
    config: dict[str, str],
    story_data_text: str,
    current_package: dict[str, str],
) -> dict[str, Any]:
    prompt_data = {
        **config,
        "story_data": story_data_text,
        "crime_narrative": current_package["crime_generation"],
        "side_stories": current_package["side_stories_generation"],
        "surface_level": current_package["surface_level_generation"],
        "agendas": current_package["agendas_generation"],
        "investigation": current_package["investigation_generation"],
    }
    system_instruction, prompt = build_prompt("critic_persona", _PROMPT_DIR, prompt_data)

    generation_params = GenerationParams(
        max_tokens=15000,
        temperature=1.2,
        top_p=0.9,
        top_k=20,
        repetition_penalty=0,
        response_type="text/plain",
        include_thoughts=_INCLUDE_THOUGHTS,
        thinking_budget=_DEFAULT_THINKING_BUDGET,
    )
    response = llm.generate(prompt, system_instruction, generation_params)
    return {
        "prompt": prompt,
        "system_instruction": system_instruction,
        "generation_params": generation_params,
        "generation_result": response,
    }


def _call_leader(
    llm: LLM,
    critic_configs: list[dict[str, str]],
    critiques: list[str],
    story_data_text: str,
    current_package: dict[str, str],
) -> dict[str, Any]:
    critique_blocks: list[str] = []
    for config, critique_text in zip(critic_configs, critiques):
        critique_blocks.append(
            f"── Critique from {config['persona_name']} (criterion: {config['criterion_name']}) ──\n"
            f"{critique_text}"
        )

    prompt_data = {
        "story_data": story_data_text,
        "crime_narrative": current_package["crime_generation"],
        "side_stories": current_package["side_stories_generation"],
        "surface_level": current_package["surface_level_generation"],
        "agendas": current_package["agendas_generation"],
        "investigation": current_package["investigation_generation"],
        "all_critiques": "\n\n".join(critique_blocks),
    }
    system_instruction, prompt = build_prompt("critic_leader", _PROMPT_DIR, prompt_data)

    generation_params = GenerationParams(
        max_tokens=60000,
        temperature=0.8,
        top_p=0.9,
        top_k=20,
        repetition_penalty=0,
        response_type="text/plain",
        include_thoughts=_INCLUDE_THOUGHTS,
        thinking_budget=_DEFAULT_THINKING_BUDGET,
    )
    response = llm.generate(prompt, system_instruction, generation_params)
    return {
        "prompt": prompt,
        "system_instruction": system_instruction,
        "generation_params": generation_params,
        "generation_result": response,
    }


def _call_evaluator(
    llm: LLM,
    story_data_text: str,
    crime_narrative: str,
    side_stories: str,
    versions: list[dict[str, str]],
) -> dict[str, Any]:
    version_blocks: list[str] = []
    for idx, package in enumerate(versions):
        if idx == 0:
            label = "VERSION 0 (Original — before critique)"
        else:
            label = f"VERSION {idx} (After critique round {idx})"
        version_blocks.append(f"── {label} ──\n{_format_package_text(package)}")

    prompt_data = {
        "story_data": story_data_text,
        "crime_narrative": crime_narrative,
        "side_stories": side_stories,
        "all_versions": "\n\n".join(version_blocks),
    }
    system_instruction, prompt = build_prompt("critic_evaluator", _PROMPT_DIR, prompt_data)

    generation_params = GenerationParams(
        max_tokens=60000,
        temperature=0.5,
        top_p=0.9,
        top_k=5,
        repetition_penalty=0,
        response_type="text/plain",
        include_thoughts=_INCLUDE_THOUGHTS,
        thinking_budget=_DEFAULT_THINKING_BUDGET,
    )
    response = llm.generate(prompt, system_instruction, generation_params)
    return {
        "prompt": prompt,
        "system_instruction": system_instruction,
        "generation_params": generation_params,
        "generation_result": response,
    }


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _extract_package_block(text: str) -> str | None:
    start = text.find(_REVISED_PACKAGE_START)
    if start == -1:
        return None
    start += len(_REVISED_PACKAGE_START)
    end = text.find(_REVISED_PACKAGE_END, start)
    if end == -1:
        end = len(text)
    return text[start:end].strip()


def _parse_revised_package(text: str, base_package: dict[str, str]) -> dict[str, str]:
    block = _extract_package_block(text) or text
    matches = list(_STAGE_HEADER_RE.finditer(block))
    if not matches:
        return dict(base_package)

    revised = dict(base_package)
    for idx, match in enumerate(matches):
        stage_name = match.group(1).strip()
        if stage_name not in _CRITIC_STAGE_ORDER:
            continue
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(block)
        content = block[start:end].strip()
        if not content or content == "[UNCHANGED]":
            continue
        revised[stage_name] = content

    return revised


def _format_package_text(package: dict[str, str]) -> str:
    lines = [_REVISED_PACKAGE_START, ""]
    for stage_name in _CRITIC_STAGE_ORDER:
        lines.append(f"### STAGE: {stage_name}")
        lines.append(package.get(stage_name, ""))
        lines.append("")
    lines.append(_REVISED_PACKAGE_END)
    return "\n".join(lines).strip()


def _next_critics_run_index(story_directory: StoryDirectory) -> int:
    """Return the next run index for critics_<NN> artifacts."""
    indices: set[int] = set()

    run_pattern = re.compile(r"^critics_(\d+)_")
    for name in os.listdir(story_directory.path):
        match = run_pattern.match(name)
        if match:
            indices.add(int(match.group(1)))

    return (max(indices) + 1) if indices else 0