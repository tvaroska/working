from typing import List
import json
from datetime import datetime, timedelta

from pydantic import BaseModel, Field
from tqdm import tqdm
from updater.collect import new_articles
from langchain_google_vertexai import ChatVertexAI

class Summary(BaseModel):
    title: str = Field(description='Title of the article')
    short: str = Field(description='Tweet like summary of the article')
    long: str = Field(description='Summary of the article in form of independent text. Length of the text should be 250 words. Audience of this new version will consume it on the mobile phone during their commute. Respond in Markdown, each point as header3 and short support text for point.')
#    links: List[str] = Field(description='If article refer to another interesting informations, list of urls')

with open('settings.json') as f:
    data = json.load(f)

starting_point = datetime.now() - timedelta(weeks=16)

articles = new_articles(data['feeds'], starting_point=starting_point)

summarizer = ChatVertexAI(model='gemini-1.5-flash-002').with_structured_output(Summary, method='json_mode')

output = []
for item in tqdm(articles):
    summary = summarizer.invoke([
        ("user", [{"type": "text", "text": "Analyze the article"}, 
              {"type": "media", "mime_type": item.mime_type, "file_uri": item.url}])
    ])
    output.append(summary)

with open('articles.json', 'w+') as f:
    json.dump([item.model_dump_json() for item in output], f)