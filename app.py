from fastapi import FastAPI

import search

DB_URI="postgresql+psycopg://postgres:postgres@localhost/search"

search_instance = search.Search('working')
router = search_instance.get_router()

app = FastAPI()
app.include_router(router)
