from pathlib import Path
from typing import Dict, List


class MapFolderManager:
    map_list: dict = {}

    def __init__(self) -> None:
        try:
            maps = self.get_all_maps()
            self.map_list = self.map_name_dict(maps)
        except Exception as e:
            raise FileNotFoundError(e)

    def get_all_maps(self) -> list:
        maps = Path("/home/mehdemir/Projects/Fly/maps").rglob("*.txt")
        map_list = sorted(list(maps))

        if not map_list:
            raise FileNotFoundError("Maps couldn't located.")

        return map_list

    def map_name_dict(self, map_list: List[Path]) -> dict:
        map_dict: Dict = {}

        for i in map_list:
            splitted = i.stem.split("_", 1)
            map_dict[i.name] = {
                "name": splitted[1].replace("_", " ").title(), #will give an error if there is no _ in the name
                "category": i.parent.name,
                "number": splitted[0],
                "address": i
            }
        return map_dict


if __name__ == "__main__":
    a = MapFolderManager()
    print(a.map_list)
