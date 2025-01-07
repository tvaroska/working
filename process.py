import json

from datetime import datetime, timedelta
from updater.collect import new_articles

with open('settings.json') as f:
    data = json.load(f)

starting_point = datetime.now() - timedelta(weeks=16)

articles = new_articles(data['feeds'], starting_point=starting_point)

print(len(articles))