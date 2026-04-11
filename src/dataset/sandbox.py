import os
import json
import pandas as pd
import wikipediaapi

bmds_df = pd.read_csv("datasets/BMDS/BMDS_story_annotations.csv")

present_in_bmds = 0
missing_from_bmds = 0
with open("datasets/wikidata/literary/data.jsonl", "r") as wiki:
    wikidata_works = [json.loads(line) for line in wiki.readlines()]
    wikidata_titles = {work["title"].lower() for work in wikidata_works}
    
    for _, row in bmds_df.iterrows():
        title = row["Story Title"].lower().strip()
        if title in wikidata_titles:
            present_in_bmds += 1
            wikidata_titles.remove(title)
        else:
            missing_from_bmds += 1
            print(f"Missing from Wikidata: {row['Story Title']}")


print(f"Total works in BMDS: {len(bmds_df)}")
print(f"Present in Wikidata: {present_in_bmds}")
print(f"Missing from Wikidata: {missing_from_bmds}")
