from fastapi import APIRouter, Depends, BackgroundTasks

class Search:

    def __init__(self, message):
        self.router = APIRouter()
        self.message = message

        self.router.add_api_route("/", self.ping, methods=["GET"])
        self.router.add_api_route(
            "/ingest",
            self.ingest,
            methods=["POST"],
#            dependencies=[Depends(BackgroundTasks)]
        )
        self.router.add_api_route("/search", self.search, methods=["POST"])

    def ping(self):
        return {"msg": self.message}

    def ingest(self, background: BackgroundTasks):
        print(background)
        pass

    def search(self):
        return {"test": "works"}

    def get_router(self) -> APIRouter:
        return self.router
