import json
from app import user_input
from app import crime_graph
from app.schemas.user_input import InputData
from app.schemas.crime_graph import ActorPool
from demo.llm.google_llm import GoogleLLM
from demo.serialization import StoryDirectory

if __name__ == "__main__":
    api_key = ""
    with open("src/demo/cred.json", "r") as f:
        cred = json.load(f)
        api_key = cred["google_api_key"]

    llm = GoogleLLM(model_id="gemini-2.5-flash", api_key=api_key)
    print("Model loaded successfully.")
    
    story_dir = StoryDirectory.new("story", "src/stories")
    
    input_data = user_input.extract_input_data(llm, "I want to write a detective story set in Victorian London, featuring a brilliant but eccentric detective and a loyal assistant. The story should involve a mysterious murder in a grand mansion, with a cast of intriguing suspects. I want the story to have a dark and atmospheric tone, with plenty of twists and turns to keep readers guessing until the very end.", story_dir)

    #input_data_filled = user_input.fill_missing_data(llm, input_data, story_dir)
    
    # story_dir = StoryDirectory.open("2026-02-13_162716_story", "src/stories")
    
    # input_data = story_dir.load_stage("input_extraction")["response"]
    # input_data = InputData.model_validate(input_data)
    
    actor_pool = crime_graph.generate_actor_pool(llm, input_data, story_dir)
    
    # actor_pool = story_dir.load_stage("actor_generation")["response"]
    # actor_pool = ActorPool.model_validate(actor_pool)
    
    crime = crime_graph.generate_crime_graph(llm, input_data, actor_pool, story_dir)
    