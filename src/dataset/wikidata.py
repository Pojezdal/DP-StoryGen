import json
from SPARQLWrapper import SPARQLWrapper, JSON
import wikipediaapi
import os
from urllib.parse import urlparse, unquote
import requests
import time

def extract_wiki_title(url: str) -> str:
    path = urlparse(url).path
    title = path.removeprefix("/wiki/")
    return unquote(title)



session = requests.Session()
session.headers.update({
    "User-Agent": "YourProjectName/1.0 (your-email@example.com)"
})

wiki = wikipediaapi.Wikipedia(
    language="en",
    user_agent="DetectiveCorpusBuilder/1.0 (your_email@example.com)",
    timeout=30
)

endpoint_url = "https://query.wikidata.org/sparql"
literary_instances = ["Q7725634"]  # literary work
literary_genres = ["Q5937792", "Q6585139", "Q186424"]
movie_instances = ["Q11424"]  # film
movie_genres = ["Q1200678", "Q19367312", "Q25533274"] #"Q959790"
section_titles = ["plot", "summary", "plot summary", "story summary", "plot overview", "storyline", "plot outline", "plot introduction", "synopsis", "plot synopsis", "premise"]
query = """
SELECT DISTINCT ?qid ?work ?workLabel ?article ?author ?authorLabel ?pubDate WHERE {{
    ?work wdt:P31 wd:{instance};
            wdt:P136/wdt:P279* wd:{genre}.

    # Author (optional, since not all works have P50)
    OPTIONAL {{ ?work wdt:P50 ?author. }}
    
    # Director (optional, for films)
    OPTIONAL {{ ?work wdt:P57 ?author. }}

    # Publication date (optional)
    OPTIONAL {{ ?work wdt:P577 ?pubDate. }}

    # English Wikipedia article (required)
    ?article schema:about ?work;
            schema:inLanguage "en";
            schema:isPartOf <https://en.wikipedia.org/>.

    BIND(STRAFTER(STR(?work), "/entity/") AS ?qid)

    SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
"""

class WikiRecord:
    def __init__(self, qid, title, article, author, pubDate, plot):
        self.qid = qid
        self.title = title
        self.article = article
        self.authors = set()
        if author:
            self.authors.add(author)
        self.pubDate = pubDate.split("T")[0] if pubDate else None
        self.plot = plot
        
    def update_author(self, author):
        if author:
            self.authors.add(author)
            
    def update_pubDate(self, pubDate):
        if pubDate:
            if not self.pubDate or pubDate.split("T")[0] < self.pubDate:
                self.pubDate = pubDate.split("T")[0]
                
    def to_dict(self):
        return {
            "qid": self.qid,
            "title": self.title,
            "article": self.article,
            "authors": list(self.authors),
            "pubDate": self.pubDate if self.pubDate else "Unknown",
            "plot": self.plot,
        }

def fetch_wikidata_works(instances, genres):
    sparql = SPARQLWrapper(endpoint_url)
    all_results = []
    for instance in instances:
        for genre in genres:
            q = query.format(instance=instance, genre=genre)
            sparql.setQuery(q)
            sparql.setReturnFormat(JSON)
            results = sparql.query().convert()
            all_results.extend(results["results"]["bindings"])
    return all_results

results = fetch_wikidata_works(literary_instances, literary_genres)
print(f"Fetched {len(results)} works")

def merge_duplicate_works(results):
    results.sort(key=lambda x: (x.get("qid", {}).get("value", ""), x.get("authorLabel", {}).get("value", ""), x.get("workLabel", {}).get("value", ""), x.get("pubDate", {}).get("value", "")))
    merged_results = []
    last_qid = None
    for result in results:
        qid = result["qid"]["value"]
        if qid != last_qid:
            merged_results.append(WikiRecord(
                qid=qid,
                title=result["workLabel"]["value"],
                article=result["article"]["value"],
                author=result.get("authorLabel", {}).get("value", None),
                pubDate=result.get("pubDate", {}).get("value", None),
                plot=None
            ))
            last_qid = qid
        else:
            merged_results[-1].update_author(result.get("authorLabel", {}).get("value", None))
            merged_results[-1].update_pubDate(result.get("pubDate", {}).get("value", None))
    return merged_results

merged_results = merge_duplicate_works(results)
print(f"Merged to {len(merged_results)} unique works after combining duplicates")

with open("datasets/wikidata/literary/title_index.txt", "w", encoding="utf-8") as f:
    for record in merged_results:
        f.write(f"{record.title}\n")
    

def fetch_plots(results):
    successful = []
    failed = {
        "page_not_found": [],
        "no_plot_section": [],
        "plot_too_short": [],
    }
    
    for i, result in enumerate(results):
        if (i + 1) % 50 == 0:
            print(f"Fetched {i + 1}/{len(results)} works' plots")
        extracted_title = extract_wiki_title(result.article)
        page = wiki.page(extracted_title)
        time.sleep(0.5)
        if not page.exists():
            print(f"Warning: Page does not exist: {result.title}, extracted title: {extracted_title}")
            failed["page_not_found"].append(result.title)
            if result.title == "The Adventure of the Stockbroker's Clerk":
                exit()
            continue
        result.plot = None
        for section in page.sections:
            if section.title.lower() in section_titles:
                if result.plot is not None:
                    print(f"Warning: Multiple plot sections found for {result.title}: {[section.title for section in page.sections]}")
                else:
                    result.plot = section.text
        if result.plot is None:
            print(f"Warning: No plot section found for {result.title}: {[section.title for section in page.sections]}")
            failed["no_plot_section"].append(result.title)
            continue
        if len(result.plot) < 500:
            print(f"Warning: Plot section too short for {result.title}")
            failed["plot_too_short"].append(result.title)
            continue
        successful.append(result)
    return successful, failed

successful, failed = fetch_plots(merged_results)

print(f"Successfully processed {len(successful)} works, failed {sum(len(v) for v in failed.values())} works")
print("Failure breakdown:")
for reason, items in failed.items():
    print(f"  {reason}: {len(items)}")

os.makedirs("datasets/wikidata/literary", exist_ok=True)
with open(f"datasets/wikidata/literary/data.jsonl", "w") as f:
    for data in successful:
        f.write(json.dumps(data.to_dict()) + "\n")
        
with open(f"datasets/wikidata/literary/failure_report.jsonl", "w") as f:
    for reason, items in failed.items():
        for item in items:
            f.write(json.dumps({"reason": reason, "title": item}) + "\n")