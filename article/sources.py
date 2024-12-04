import os
import httpx


SOURCES = {
    # cloudfare 'https://www.coinbase.com/blog/lessons-from-launching-enterprise-grade-genAI-solutions-at-Coinbase': 'data/coinbase',
    'https://www.godaddy.com/resources/news/llm-from-the-trenches-10-lessons-learned-operationalizing-models-at-godaddy': 'data/godady',
    'https://www.oreilly.com/radar/what-we-learned-from-a-year-of-building-with-llms-part-i': 'data/oreilly1',
    'https://www.oreilly.com/radar/what-we-learned-from-a-year-of-building-with-llms-part-ii': 'data/oreilly2',
    'https://www.oreilly.com/radar/what-we-learned-from-a-year-of-building-with-llms-part-iii-strategy/': 'data/oreilly3',
    'https://www.linkedin.com/blog/engineering/generative-ai/musings-on-building-a-generative-ai-product': 'data/musing',
    # slides 'https://t.co/CwfYtceC4W':'data/liu1'
}

BASE = 'https://r.jina.ai/'

def get_sources():
    with httpx.Client(timeout=3000) as client:
        for url, fname in SOURCES.items():
            md = fname + '.md'
            if os.path.exists(md):
                print(f'{md} already exists')
                continue
            response = client.get(BASE + url)
            if response.status_code != 200:
                print(f'{url} got error {response.status_code}')
                continue
            with open(md, 'w+') as f:
                f.write(response.content.decode())

def sources():
    response = []
    for fname in SOURCES.values():
        with open(fname + '.md') as f:
            response.append((fname, f.read()))

    return response


if __name__ =='__main__':
    get_sources()