import logging

from typing import List
import json
from datetime import datetime, timedelta

import asyncio

from pydantic import BaseModel, Field
from tqdm.asyncio import tqdm
from updater.collect import new_articles, Article

from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type
from google import genai
from google.genai.types import Part, GenerateContentConfig
from google.genai.errors import ClientError

# Logging setup
logging.basicConfig(filename='collect.log', filemode='w', format='%(levelname)s:%(message)s', level=logging.ERROR)


class Summary(BaseModel):
    short: str = Field(description='Tweet like summary of the article')
    long: str = Field(description='Summary of the article in form of independent text. Length of the text should be 250 words. Audience of this new version will consume it on the mobile phone during their commute. Respond in Markdown, each point as header3 and short support text for point.')

class ResourceExaused(ClientError):
    pass

semaphore = asyncio.Semaphore(10)
gemini = genai.Client(vertexai=True, location='us-central1')

@retry(stop=stop_after_attempt(4), 
       wait=wait_exponential_jitter(initial=10, jitter=5),
       retry=retry_if_exception_type(ResourceExaused))
async def get_summary(article: Article) -> Article:
    async with semaphore:
        try:
            response = await gemini.aio.models.generate_content(
                model='gemini-1.5-flash-002',
                contents=[
                    Part.from_text("Analyze the article"),
                    Part.from_uri(article.url, mime_type=article.mime_type)
                ],
                config=GenerateContentConfig(
                    response_mime_type= 'application/json',
                    response_schema=Summary,
                )
            )
        except ClientError as e:
            if e.code == 429:
                raise ResourceExaused(code=e.code, response = e.response) from e
            elif e.code == 400: # cannot load
                logging.error(msg=article.url)
                return None
            else:
                raise ClientError(code=e.code, response=e.response) from e
    summary = Summary.model_validate_json(response.text)

    article.short_summary = summary.short
    article.summary = summary.long

    return article


async def main():

    with open('settings.json') as f:
        data = json.load(f)

    starting_point = datetime.now() - timedelta(weeks=52)
    articles = await new_articles(data['feeds'], starting_point=starting_point)
    tasks = [get_summary(article) for article in articles]

    updated_articles = await tqdm.gather(*tasks)

    with open('articles.json', 'w+') as f:
        json.dump(
            {"date": datetime.now().strftime("%b %d %Y"),
             "updated": [
                 {
                     "title": item.title,
                     "short": item.short_summary,
                     "long": item.summary,
                     "url": item.url
                 } for item in updated_articles if item]
            }, f)


if __name__ == '__main__':
    asyncio.run(main())