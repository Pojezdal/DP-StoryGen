import json

from final.pipeline_full.pipeline import load_or_execute_stage
from final.pipeline_full.critics import critique_investigation_package
from final.pipeline_full.chapter_generation import generate_chapters
from final.pipeline_full import chapter_package_extractor
from final.pipeline_full.schemas.story_data import StoryData
from final.utils import StoryDirectory
from final.llm.llm import GenerationParams, GenerationResult
from final.llm.google_llm import GoogleLLM


if __name__ == "__main__":
    with open("cred.json", "r") as f:
        cred = json.load(f)
        api_keys = cred["google_api_keys"]

    llm_primary = GoogleLLM(model_id="gemini-3-flash-preview", api_keys=api_keys)
    llm_secondary = GoogleLLM(model_id="gemini-2.5-flash", api_keys=api_keys)
    llm_tertiary = GoogleLLM(model_id="gemini-3.1-flash-lite-preview", api_keys=api_keys)
    print("Models loaded successfully.")
    
    #story_directory = StoryDirectory.new()
    story_directory = StoryDirectory.open("2026-04-07_155143")
    
    story_data = load_or_execute_stage("story_data_generation", llm_primary, story_directory, force_execute=False, schema=StoryData,
        user_input=
        "I want to write a detective story set in a small country english town "
        "at the turn of the 20th and 21st century. The story should have somewhat "
        "lighter atmosphere, with some comedic elements, but still with an "
        "intriguing and engaging crime at the center. The main character is an old "
        "retired detective who was just planning a quiet holiday in the countryside, "
        "but then gets drawn into solving a crime that happens in the town. The "
        "murder should be elaborate and complex with surprising twist. The story "
        "should somehow include local church, and a post in an old local newspapers "
        "should play important role in the investigation."
    )
    
    crime = load_or_execute_stage("crime_generation", llm_primary, story_directory, force_execute=False, story_data=story_data)
    
    side_stories = load_or_execute_stage(
        "side_stories_generation",
        llm_primary,
        story_directory,
        force_execute=False,
        story_data=story_data,
        crime_narrative=crime,
    )

    surface_level = load_or_execute_stage(
        "surface_level_generation",
        llm_primary,
        story_directory,
        force_execute=False,
        story_data=story_data,
        crime_narrative=crime,
        side_stories=side_stories,
    )

    agendas = load_or_execute_stage(
        "agendas_generation",
        llm_primary,
        story_directory,
        force_execute=False,
        story_data=story_data,
        crime_narrative=crime,
        side_stories=side_stories,
        surface_level=surface_level,
    )

    investigation = load_or_execute_stage(
        "investigation_generation",
        llm_primary,
        story_directory,
        force_execute=False,
        story_data=story_data,
        crime_narrative=crime,
        side_stories=side_stories,
        surface_level=surface_level,
        agendas=agendas,
    )
    
    critics_package = critique_investigation_package(
        llm=llm_primary,
        story_directory=story_directory,
        story_data=story_data,
        crime_narrative=crime,
        side_stories=side_stories,
        surface_level=surface_level,
        agendas=agendas,
        investigation=investigation,
        run_index=1
    )

    architecture = load_or_execute_stage(
        "architecture_generation",
        llm_primary,
        story_directory,
        force_execute=False,
        story_data=story_data,
        crime_narrative=critics_package.get("crime_generation", crime),
        side_stories=critics_package.get("side_stories_generation", side_stories),
        surface_level=critics_package.get("surface_level_generation", surface_level),
        agendas=critics_package.get("agendas_generation", agendas),
        investigation=critics_package.get("investigation_generation", investigation),
    )

    chapter_outline = load_or_execute_stage(
        "chapter_outline_generation",
        llm_primary,
        story_directory,
        force_execute=False,
        story_data=story_data,
        crime_narrative=critics_package.get("crime_generation", crime),
        side_stories=critics_package.get("side_stories_generation", side_stories),
        surface_level=critics_package.get("surface_level_generation", surface_level),
        agendas=critics_package.get("agendas_generation", agendas),
        investigation=critics_package.get("investigation_generation", investigation),
        architecture=architecture,
    )

    chapter_packages = chapter_package_extractor.save_chapter_packages(
        story_directory=story_directory,
        story_data=story_data,
        chapter_outline=chapter_outline,
        architecture=architecture,
        crime_narrative=critics_package.get("crime_generation", crime),
        side_stories=critics_package.get("side_stories_generation", side_stories),
        agendas=critics_package.get("agendas_generation", agendas),
        investigation=critics_package.get("investigation_generation", investigation),
    )
    
    generate_chapters(
        llm=llm_primary,
        story_directory=story_directory,
        package_data=chapter_packages,
        start_chapter=1,
        end_chapter=2
    )