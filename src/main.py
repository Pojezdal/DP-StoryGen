import json
import random
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
    
    #story_dir = StoryDirectory.new("story", "src/stories")
    
    #input_data = user_input.extract_input_data(llm, "I want to write a detective story set in a small country english town at the turn of the 20th and 21st century. The story should somewhat lighter atmosphere, with some comedic elements, but still with an intriguing and engaging crime at the center. The main character is an old retired detective who was just planning a quiet holiday in the countryside, but then gets drawn into solving a crime that happens in the town. The murder should be elaborate and complex with surprising twist with the murder itself being caused by an unknowing third party. The story should somehow include local church and a post in an old local newspapers should play important role in the investigation.", story_dir)

    #input_data_filled = user_input.fill_missing_data(llm, input_data, story_dir)
    
    story_dir = StoryDirectory.open("2026-02-20_161409_story", "src/stories")
    
    input_data = story_dir.load_stage("input_extraction")["response"]
    input_data = InputData.model_validate(input_data)
    
    #actor_pool = crime_graph.generate_actor_pool(llm, input_data, story_dir)
    
    actor_pool = story_dir.load_stage("actor_generation")["response"]
    actor_pool = ActorPool.model_validate(actor_pool)
    
    #crime = crime_graph.generate_crime_graph(llm, input_data, actor_pool, story_dir)
    
    crime = story_dir.load_stage("crime_generation")["response"]
    crime = crime_graph.CrimeGraph.model_validate(crime)
    
    #backgrounds = crime_graph.generate_suspect_backgrounds(llm, input_data, actor_pool, crime, story_dir)
    
    backgrounds = story_dir.load_stage("suspect_backgrounds_generation")["response"]
    backgrounds = crime_graph.SuspectBackgrounds.model_validate(backgrounds)
    
    investigation = crime_graph.generate_investigation_graph(llm, input_data, actor_pool, crime, backgrounds, story_dir)
    