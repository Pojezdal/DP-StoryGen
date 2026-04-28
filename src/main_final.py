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
    story_directory = StoryDirectory.open("2026-04-27_173704")
    
    story_data : StoryData = load_or_execute_stage("story_data_generation", llm_primary, story_directory, force_execute=False, schema=StoryData,
        user_input=
        "Write a detective story set in a small coastal town during the off-season. The story begins with the discovery of a body in a locked room inside a lighthouse. The main character is a retired detective visiting the town who becomes involved reluctantly. "
        "Include exactly four main suspects: the lighthouse keeper, a local journalist, a visiting tourist, and a town official. Each suspect must have a clear motive, a hidden secret, and at least one false alibi. Provide at least five concrete clues discovered during the investigation, and ensure all of them are relevant to solving the case. "
        "The investigation should include interviews, examination of the crime scene, and at least one misleading lead. The true solution must rely only on information presented earlier and should not introduce new facts at the end. Include one major twist that changes the interpretation of earlier events. "
        "Keep the tone slightly light with occasional humor, but maintain a coherent and logically solvable mystery. Avoid supernatural elements and ensure the culprit is one of the four suspects."
        
        #"Write a gripping detective story set in a rain-soaked coastal town where the murder victim is someone widely disliked but secretly connected to every major suspect. The detective should be deeply flawed—perhaps struggling with a personal loss or hiding something from their past—and must solve the case within 48 hours before a storm cuts the town off completely. Include exactly four suspects, each with a clear motive but also a convincing alibi that gradually unravels. The murder weapon should seem ordinary at first but turn out to have an unexpected significance tied to the victim’s hidden life. Avoid using any modern forensic technology; rely instead on dialogue, observation, and psychological tension. End with a twist where the true culprit is the one person the detective trusted most, and make sure the final reveal forces the detective to confront their own moral boundaries."
        
        #"Write me a gritty, atmospheric detective story set in a city where it never fully gets dark, even at midnight. The main character is a morally conflicted detective who hasn’t slept in three days and keeps seeing things that may or may not be real. The story must unfold over the course of a single night and include exactly three suspects, each with a believable motive but only one who is actually guilty. Don’t reveal who the culprit is until the final paragraph, but plant subtle clues throughout that would allow a careful reader to figure it out earlier. Include at least one scene that takes place in a moving vehicle and one tense interrogation where no one explicitly lies but no one tells the full truth either. Avoid clichés, don’t use any supernatural explanations (even if it seems like there might be one), and end with a resolution that feels unsettling rather than satisfying."
        
        
        # "Write a detective story set in a small coastal city where the weather is almost always foggy, but avoid making the fog just a mood detail—it should actively interfere with clues, movement, or perception in at least one important investigation scene. The detective should not be a stereotypical genius or a hard-drinking cliché; instead, give them a very specific limitation (like poor memory for faces, color blindness, or an unusual fear that affects their work) that actually matters to the case. "
        # "The mystery should revolve around an apparently impossible crime that has a simple but emotionally complicated explanation rather than a flashy twist. Avoid overused tropes like secret twin identities or the villain monologuing at the end. Let at least one key piece of evidence be something easily overlooked in real life, not a dramatic object like a bloody knife or coded letter. The resolution should feel fair—readers should be able to trace the logic—but still slightly unsettling because of what it reveals about ordinary people rather than extraordinary evil."
        
        
        #"Write a detective story set in a near-future city where analog technology is making a quiet comeback. The protagonist is a mildly disgraced forensic linguist who can no longer use AI tools and must rely entirely on human intuition and outdated methods like typewriters, cassette tapes, and handwritten notes. The central mystery should revolve around a series of seemingly unrelated voice messages left on public payphones, all containing subtle linguistic patterns that hint at a larger conspiracy. Include at least three suspects, each with believable motives but no obvious villain, and ensure the true culprit is revealed through a non-obvious linguistic clue rather than physical evidence. Avoid any violent confrontations or chase scenes; the tension should come from intellectual discovery and moral ambiguity. Incorporate a secondary theme about memory degradation—either technological or human—and end with a resolution that solves the case but leaves one unsettling question unanswered."
        
        
        # "Write a detective story set aboard a long-distance overnight train traveling through a remote, snow-covered mountain region in the late 1980s. The atmosphere should feel tense and claustrophobic, with moments of dry humor and subtle character-driven wit. "
        # "The protagonist is a meticulous but socially awkward railway safety inspector who initially boards the train to investigate minor procedural violations. When a passenger is found dead in a locked sleeper cabin under seemingly impossible circumstances, they are forced to take on the role of an investigator."
        
        
        # "I want to write a detective story that is radically different from a classic "
        # "village whodunit: set it on a near-future deep-sea research habitat anchored at the " 
        # "bottom of the Norwegian Sea during a 72-hour storm blackout, where no one can surface without dying. "
        # "The protagonist is not a retired inspector but a young forensic linguist with partial hearing loss, "
        # "brought in to decode emergency voice logs after the habitat director is found dead inside a "
        # "pressure-sealed bioluminescence lab that was supposedly never opened. Keep the tone tense, "
        # "cerebral, and atmospheric, with brief moments of dry humor from crew dynamics, but no cozy feel. "
        # "The core mystery should combine physical evidence, language evidence, and systems evidence: conflicting "
        # "transcript fragments, maintenance command logs, oxygen usage anomalies, and subtle contamination patterns "
        # "in seawater samples. Build a suspect circle of scientists, engineers, and contractors with clashing "
        # "professional incentives, old betrayals, and one hidden relationship that changes the motive landscape. "
        # "Make the crime method technically plausible and explainable step by step, with at least two serious "
        # "complications that force the culprit to improvise and leave unintended trace evidence. "
        # "Include fair-play clues early, at least two strong red herrings, and one false-solution reveal "
        # "before the true solution. End with a twist that reinterprets the opening emergency message in a "
        # "logically consistent way, proving the detective was misreading not the words, but the speaker context.",
        
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
        run_index=0,
        num_rounds=3
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