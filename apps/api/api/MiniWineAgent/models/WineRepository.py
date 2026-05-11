import json

from .Wine import Wine


class WineRepository:

    def __init__(self, path: str):
        self.path = path

    def get_by_id(self, wine_id: int):

        with open(self.path) as f:
            data = json.load(f)

        for wine_data in data:

            if wine_data["id"] == wine_id:
                return Wine(**wine_data)

        return None
