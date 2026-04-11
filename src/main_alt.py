"""Alternative pipeline entry point.

Pipeline:
  1. (reuse) Extract input data from user prompt
  2. Generate lean actor pool (no motive/method/means on suspects)
  3. Select culprit (random or specified)
  4. Generate free-form crime narrative (unconstrained text)
  5. Parse narrative into CrimeTimeline (mechanical JSON extraction)
  6. (optional) Validate the parsed timeline

Run:  python -m main_alt
From:  src/
"""

import json
import os
import re
from app import user_input
from app import alt_pipeline
from app.schemas.user_input import InputData
from app.schemas.actor_generation_lean import LeanActorPool
from app.schemas.action_state_graph import CrimeTimeline
from app import chapter_package_extractor
from app import chapter_generation
from demo.llm.google_llm import GoogleLLM
from demo.serialization import StoryDirectory
from google import genai


if __name__ == "__main__":    
    # ── credentials ──────────────────────────────────────────────────────
    with open("src/demo/cred.json", "r") as f:
        cred = json.load(f)
        api_keys = cred["google_api_keys"]

    #llm = GoogleLLM(model_id="gemini-2.5-flash", api_key=api_key)
    llm = GoogleLLM(model_id="gemini-3-flash-preview", api_keys=api_keys)
    llm_validation = GoogleLLM(model_id="gemini-3.1-flash-lite-preview", api_keys=api_keys)
    print("Model loaded successfully.")

    # ── story directory ──────────────────────────────────────────────────
    # Create a new story directory for the alt pipeline run
    #story_dir = StoryDirectory.new("story", "src/stories")
    
    # ── Stage 0: input extraction (reuse existing) ───────────────────────
    # input_data = user_input.extract_input_data(
    #     llm,
        # "I want to write a detective story set in a small country english town "
        # "at the turn of the 20th and 21st century. The story should have somewhat "
        # "lighter atmosphere, with some comedic elements, but still with an "
        # "intriguing and engaging crime at the center. The main character is an old "
        # "retired detective who was just planning a quiet holiday in the countryside, "
        # "but then gets drawn into solving a crime that happens in the town. The "
        # "murder should be elaborate and complex with surprising twist. The story "
        # "should somehow include local church, and a post in an old local newspapers "
        # "should play important role in the investigation.",
    #     story_dir,
    # )
    
    # input_data = user_input.extract_input_data(
    #     llm,
    #     """I want to write a detective story that is radically different from a classic 
    #     village whodunit: set it on a near-future deep-sea research habitat anchored at the 
    #     bottom of the Norwegian Sea during a 72-hour storm blackout, where no one can surface without dying. 
    #     The protagonist is not a retired inspector but a young forensic linguist with partial hearing loss, 
    #     brought in to decode emergency voice logs after the habitat director is found dead inside a 
    #     pressure-sealed bioluminescence lab that was supposedly never opened. Keep the tone tense, 
    #     cerebral, and atmospheric, with brief moments of dry humor from crew dynamics, but no cozy feel. 
    #     The core mystery should combine physical evidence, language evidence, and systems evidence: conflicting 
    #     transcript fragments, maintenance command logs, oxygen usage anomalies, and subtle contamination patterns 
    #     in seawater samples. Build a suspect circle of scientists, engineers, and contractors with clashing 
    #     professional incentives, old betrayals, and one hidden relationship that changes the motive landscape. 
    #     Make the crime method technically plausible and explainable step by step, with at least two serious 
    #     complications that force the culprit to improvise and leave unintended trace evidence. 
    #     Include fair-play clues early, at least two strong red herrings, and one false-solution reveal 
    #     before the true solution. End with a twist that reinterprets the opening emergency message in a 
    #     logically consistent way, proving the detective was misreading not the words, but the speaker context.""",
    #     story_dir,
    # )

    # ── Or load existing input data: ─────────────────────────────────────
    #story_dir = StoryDirectory.open("2026-03-29_202547_story", "src/stories")
    story_dir = StoryDirectory.open("test", "src/stories")
    input_data = story_dir.load_stage("input_extraction")["response"]
    input_data = InputData.model_validate(input_data)

    # ── Stage 1: lean actor pool ─────────────────────────────────────────
    #actor_pool = alt_pipeline.generate_lean_actor_pool(llm, input_data, story_dir)
    actor_pool = story_dir.load_stage("alt_actor_generation")["response"]
    actor_pool = LeanActorPool.model_validate(actor_pool)
    print(f"Generated {len(actor_pool.suspects)} suspects, victim: {actor_pool.victim.name}")

    # ── Stage 2: culprit selection ───────────────────────────────────────
    #culprit = alt_pipeline.select_culprit(actor_pool)  # random
    culprit = alt_pipeline.select_culprit(actor_pool, culprit_name="Dr. Julian Thorne")
    #culprit = alt_pipeline.select_culprit(actor_pool, culprit_name="Sarah Sullivan")
    print(f"Culprit: {culprit.name}")

    # ── Stage 3: free-form crime narrative ───────────────────────────────
    # narrative = alt_pipeline.generate_crime_narrative(
    #     llm, input_data, actor_pool, culprit, story_dir
    # )
    narrative = story_dir.load_stage("alt_crime_narrative")["response"]
    print(f"Crime narrative generated ({len(narrative)} chars)")

    # ── Stage 3 (validation): validate crime narrative (search grounded) ──
    # validated_narrative = alt_pipeline.validate_crime_narrative(
    #     llm_validation, culprit, narrative, story_dir
    # )
    # print(f"Validated crime narrative ({len(validated_narrative)} chars)")

    # # ── Stage 3b: suspect backstories ────────────────────────────────────
    # backstories = alt_pipeline.generate_suspect_backstories(
    #     llm, input_data, actor_pool, culprit, narrative, story_dir
    # )
    backstories = story_dir.load_stage("alt_suspect_backstories")["response"]
    print(f"Suspect backstories loaded ({len(backstories)} chars)")

    # # ── Stage 3d: investigation beats (3-pass) ─────────────────────────────
    # surface_layer = alt_pipeline.generate_investigation_beats_surface_level(
    #     llm, input_data, actor_pool, narrative, backstories, story_dir
    # )
    surface_layer = story_dir.load_stage("alt_beats_surface_level")["response"]
    surface_interpretation = alt_pipeline.build_surface_interpretation(surface_layer)
    print(f"Surface interpretation layer generated ({len(surface_layer)} chars)")
    # agendas_layer = alt_pipeline.generate_investigation_beats_agendas(
    #     llm,
    #     input_data,
    #     actor_pool,
    #     narrative,
    #     backstories,
    #     surface_interpretation,
    #     story_dir,
    # )
    agendas_layer = story_dir.load_stage("alt_beats_agendas")["response"]
    post_crime_dynamics = alt_pipeline.build_post_crime_dynamics(agendas_layer)
    print(f"Post-crime dynamics layer generated ({len(agendas_layer)} chars)")
    # investigation_layer = alt_pipeline.generate_investigation_beats_investigation(
    #     llm,
    #     input_data,
    #     actor_pool,
    #     narrative,
    #     backstories,
    #     surface_interpretation,
    #     post_crime_dynamics,
    #     story_dir,
    # )
    investigation_layer = story_dir.load_stage("alt_beats_investigation")["response"]
    print(f"Investigation layer generated ({len(investigation_layer)} chars)")
    
    # investigation_beats = alt_pipeline.assemble_investigation_beats(
    #     surface_layer,
    #     agendas_layer,
    #     investigation_layer,
    #     story_directory=story_dir,
    # )
    investigation_beats = story_dir.load_stage("alt_investigation_beats")["response"]
    print(f"Investigation beats assembled ({len(investigation_beats)} chars)")
    
    # investigation_beats_parsed = alt_pipeline.parse_investigation_synthesis(
    #     llm,
    #     investigation_beats,
    #     story_dir,
    # )
    # print(f"Investigation beats parsed.")
    
    # critiques = [
    #     story_dir.load_stage("alt_critique_r1_critic_the_fair-play_advocate")["response"],
    #     story_dir.load_stage("alt_critique_r1_critic_the_twist_architect")["response"],
    #     story_dir.load_stage("alt_critique_r1_critic_the_character_psychologist")["response"],
    # ]
    
    # leader_raw = alt_pipeline._call_leader(
    #     llm=llm,
    #     culprit_name=culprit.name,
    #     crime_narrative=narrative,
    #     suspect_backstories=backstories,
    #     actor_pool_summary=alt_pipeline._format_actor_pool_summary(actor_pool),
    #     story_arc_skeleton=investigation_beats,
    #     critiques=critiques,
    #     critic_configs=alt_pipeline.DEFAULT_INVESTIGATION_BEATS_CRITIC_CONFIGS,
    #     story_directory=story_dir,
    #     round_num=1,
    # )
    # current_beats = alt_pipeline._extract_investigation_beats(leader_raw)
    # story_dir.save_plain_text(
    #     "alt_critique_final_investigation_beats", current_beats
    # )
    
    
    # critique_beats = alt_pipeline.critique_investigation_beats(
    #     llm, culprit, narrative, backstories, investigation_beats, story_dir,
    #     actor_pool=actor_pool,
    #     num_rounds=1,          # configurable: 1-3 recommended
    #     critic_configs=None,   # None = use DEFAULT_INVESTIGATION_BEATS_CRITIC_CONFIGS
    # )
    critique_beats = story_dir.load_stage("alt_critique_final_investigation_beats")["response"]
    print(f"Critiqued investigation beats loaded ({len(critique_beats)} chars)")

    # beats_architecture = alt_pipeline.generate_beats_architecture(
    #     llm,
    #     input_data,
    #     actor_pool,
    #     narrative,
    #     backstories,
    #     critique_beats,
    #     story_dir,
    # )
    beats_architecture = story_dir.load_stage("alt_beats_architecture")["response"]
    print(f"Beats architecture generated ({len(beats_architecture)} chars)")

    # beats_chapter_outlines = alt_pipeline.generate_beats_chapter_outlines(
    #     llm,
    #     input_data,
    #     actor_pool,
    #     narrative,
    #     backstories,
    #     critique_beats,
    #     beats_architecture,
    #     story_dir,
    # )
    beats_chapter_outlines = story_dir.load_stage("alt_beats_chapter_outlines")["response"]
    print(f"Beats chapter outlines generated ({len(beats_chapter_outlines)} chars)")
    
    chapter_package_extractor.save_chapter_packages(story_dir, "chapter_packages", "chapter_packages_validation")

    # ── Stage 4d: chapter text generation from chapter packages ─────────────
    # Set to True to generate chapter prose with automatic previous-chapter
    # handoff chaining.
    run_chapter_generation = False
    if run_chapter_generation:
        generated = chapter_generation.generate_chapters_from_packages(
            llm=llm,
            story_directory=story_dir,
            package_file_name="chapter_packages.json",
            start_chapter=3,
            word_min=1200,
            word_max=2000,
        )
        print(f"Generated chapter texts: {len(generated)}")

    # ── Stage 4e: compile generated chapters into one final file ───────────
    # Set to True to build one final manuscript from existing chapter_XX.txt
    # files. This does not call the LLM and can be run independently.
    run_chapter_compilation = False
    if run_chapter_compilation:
        compiled = chapter_generation.compile_chapters_to_final_file(
            story_directory=story_dir,
            output_file_stage="alt_final_story_compiled",
            output_file_name="final_story",
            start_chapter=1,
            end_chapter=None,
            header_template="CHAPTER {num_padded}",
        )
        print(
            "Compiled final story "
            f"({compiled['chapter_count']} chapters) -> {compiled['output_file']}"
        )
    

    # # ── Stage 3c: parse suspect backstories ──────────────────────────────
    # # parsed_backstories = alt_pipeline.parse_suspect_backstories(
    # #     llm, actor_pool, culprit, backstories, story_dir
    # # )
    # # print(f"Parsed backstories: {len(parsed_backstories.backstories)} suspects")
    # # for bs in parsed_backstories.backstories:
    # #     tag = " [CULPRIT]" if bs.is_culprit else ""
    # #     print(f"  - {bs.suspect_name}{tag}: {len(bs.timeline)} events, {len(bs.cross_sightings)} cross-sightings, motive={bs.motive_type.value}")

    # # ── Stage 4: story arc skeleton ───────────────────────────────────────
    # arc_skeleton = alt_pipeline.generate_story_arc_skeleton(
    #     llm,
    #     input_data,
    #     actor_pool,
    #     culprit,
    #     narrative,
    #     backstories,
    #     investigation_beats,
    #     story_dir,
    # )
    # #arc_skeleton = story_dir.load_stage("alt_story_arc_skeleton")["response"]
    # #arc_skeleton = story_dir.load_stage("alt_critique_final_skeleton")["response"]
    # print(f"Story arc skeleton generated ({len(arc_skeleton)} chars)")

    # # ── Stage 4b: validate & fix story arc skeleton ───────────────────────
    # validated_skeleton = alt_pipeline.validate_story_arc_skeleton(
    #     llm, culprit, narrative, backstories, arc_skeleton, story_dir
    # )
    # print(f"Validated story arc skeleton ({len(validated_skeleton)} chars)")

    # # ── Stage 4b (alt): CRITICS-style collective critique ─────────────────
    # critiqued_skeleton = alt_pipeline.critique_story_arc_skeleton(
    #     llm, culprit, narrative, backstories, arc_skeleton, story_dir,
    #     actor_pool=actor_pool,
    #     num_rounds=1,          # configurable: 1-3 recommended
    #     #critic_configs=None,   # None = use DEFAULT_CRITIC_CONFIGS (3 critics)
    #     critic_configs=[alt_pipeline.DEFAULT_CRITIC_CONFIGS[3]]
    # )
    # print(f"Critiqued story arc skeleton ({len(critiqued_skeleton)} chars)")

    # ── Stage 4c: chapter outline (chapter-by-chapter pacing plan) ───────
    # chapter_outline = alt_pipeline.generate_chapter_outline(
    #     llm,
    #     input_data,
    #     actor_pool,
    #     culprit,
    #     narrative,
    #     backstories,
    #     arc_skeleton,
    #     story_dir,
    # )
    # print(f"Chapter outline generated ({len(chapter_outline)} chars)")

    # Optional: validate the outline against ground truth and skeleton
    # validated_chapter_outline = alt_pipeline.validate_chapter_outline(
    #     llm,
    #     culprit,
    #     narrative,
    #     backstories,
    #     critiqued_skeleton,
    #     chapter_outline,
    #     story_dir,
    # )
    # print(f"Validated chapter outline ({len(validated_chapter_outline)} chars)")

    # ── Stage 5: parse into structured CrimeTimeline ─────────────────────
    # crime_timeline = alt_pipeline.parse_crime_narrative(
    #     llm, actor_pool, narrative, story_dir
    # )
    # print(f"Parsed timeline: {len(crime_timeline.actions)} actions")

    # ── Stage 6 (optional): validate ─────────────────────────────────────
    # validated = alt_pipeline.validate_crime_timeline(llm, actor_pool, crime_timeline, story_dir)
    # crime_timeline = validated.corrected_timeline
