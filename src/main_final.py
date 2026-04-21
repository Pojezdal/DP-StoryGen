from dataclasses import asdict
import json

from final.pipeline_full.pipeline import load_or_execute_stage
from final.pipeline_full.critics import critique_investigation_package
from final.pipeline_full.chapter_generation import generate_chapters, merge_chapters
from final.pipeline_full.detail_triple_extraction import extract_detail_triples
from final.pipeline_full.detail_triple_store import DetailTripleStore
from final.pipeline_full import chapter_package_extractor
from final.pipeline_full.schemas.story_data import StoryData
from final.utils import StoryDirectory
from final.llm.llm import GenerationParams, GenerationResult
from final.llm.google_llm import GoogleLLM
from final.llm.openrouter_llm import OpenRouterLLM


if __name__ == "__main__":
    with open("cred.json", "r") as f:
        cred = json.load(f)
        api_keys = cred["google_api_keys"]

    llm_primary = GoogleLLM(model_id="gemini-3-flash-preview", api_keys=api_keys)
    llm_secondary = GoogleLLM(model_id="gemini-2.5-flash", api_keys=api_keys)
    llm_tertiary = GoogleLLM(model_id="gemini-3.1-flash-lite-preview", api_keys=api_keys)
    print("Models loaded successfully.")
    
    #story_directory = StoryDirectory.new()
    story_directory = StoryDirectory.open("2026-04-20_154734")
    
    story_data : StoryData = load_or_execute_stage("story_data_generation", llm_primary, story_directory, force_execute=False, schema=StoryData,
        user_input=
        "I want to write a detective story that is radically different from a classic "
        "village whodunit: set it on a near-future deep-sea research habitat anchored at the " 
        "bottom of the Norwegian Sea during a 72-hour storm blackout, where no one can surface without dying. "
        "The protagonist is not a retired inspector but a young forensic linguist with partial hearing loss, "
        "brought in to decode emergency voice logs after the habitat director is found dead inside a "
        "pressure-sealed bioluminescence lab that was supposedly never opened. Keep the tone tense, "
        "cerebral, and atmospheric, with brief moments of dry humor from crew dynamics, but no cozy feel. "
        "The core mystery should combine physical evidence, language evidence, and systems evidence: conflicting "
        "transcript fragments, maintenance command logs, oxygen usage anomalies, and subtle contamination patterns "
        "in seawater samples. Build a suspect circle of scientists, engineers, and contractors with clashing "
        "professional incentives, old betrayals, and one hidden relationship that changes the motive landscape. "
        "Make the crime method technically plausible and explainable step by step, with at least two serious "
        "complications that force the culprit to improvise and leave unintended trace evidence. "
        "Include fair-play clues early, at least two strong red herrings, and one false-solution reveal "
        "before the true solution. End with a twist that reinterprets the opening emergency message in a "
        "logically consistent way, proving the detective was misreading not the words, but the speaker context.",
        
        # "I want to write a detective story set in a small country english town "
        # "at the turn of the 20th and 21st century. The story should have somewhat "
        # "lighter atmosphere, with some comedic elements, but still with an "
        # "intriguing and engaging crime at the center. The main character is an old "
        # "retired detective who was just planning a quiet holiday in the countryside, "
        # "but then gets drawn into solving a crime that happens in the town. The "
        # "murder should be elaborate and complex with surprising twist. The story "
        # "should somehow include local church, and a post in an old local newspapers "
        # "should play important role in the investigation."
    )
    
    crime = load_or_execute_stage(
        "crime_generation", 
        llm_primary, 
        story_directory, 
        force_execute=False, 
        story_data=story_data
    )
    
    suspect_briefs = load_or_execute_stage(
        "suspect_briefs_generation",
        llm_primary,
        story_directory,
        force_execute=False,
        story_data=story_data,
        crime_narrative=crime
    )
    
    clue_graph = load_or_execute_stage(
        "clue_graph_generation",
        llm_primary,
        story_directory,
        force_execute=False,
        story_data=story_data,
        crime_narrative=crime,
        suspect_briefs=suspect_briefs,
    )
    
    architecture = load_or_execute_stage(
        "architecture_generation",
        llm_primary,
        story_directory,
        force_execute=False,
        story_data=story_data,
        crime_narrative=crime,
        suspect_briefs=suspect_briefs,
        clue_graph=clue_graph,
    )
    
    critics_package = critique_investigation_package(
        llm=llm_primary,
        story_directory=story_directory,
        story_data=story_data,
        crime_narrative=crime,
        suspect_briefs=suspect_briefs,
        clue_graph=clue_graph,
        architecture=architecture,
        run_index=0
    )

    chapter_outline = load_or_execute_stage(
        "chapter_outline_generation",
        llm_primary,
        story_directory,
        force_execute=False,
        story_data=story_data,
        crime_narrative=critics_package.get("crime_generation", crime),
        suspect_briefs=critics_package.get("suspect_briefs_generation", suspect_briefs),
        architecture=critics_package.get("architecture_generation", architecture),
        #clue_graph=critics_package.get("clue_graph_generation", clue_graph),
    )

    chapter_packages = chapter_package_extractor.save_chapter_packages(
        story_directory=story_directory,
        story_data=story_data,
        chapter_outline=chapter_outline,
        crime_narrative=critics_package.get("crime_generation", crime),
        suspect_briefs=critics_package.get("suspect_briefs_generation", suspect_briefs),
        architecture=critics_package.get("architecture_generation", architecture),
        # Optional: pass clue_graph for stronger proof-chain alignment.
        # clue_graph=critics_package.get("clue_graph_generation", clue_graph),
    )
    
    generate_chapters(
        llm=llm_primary,
        story_directory=story_directory,
        package_data=chapter_packages,
        start_chapter=1,
        end_chapter=None,
        force_regenerate_chapters=False,
        extract_detail_triples_enabled=True,
        triple_extraction_llm=llm_tertiary,
        triple_extraction_actors_context=story_data.actor_pool
    )

    merge_chapters(
        story_directory=story_directory,
    )    