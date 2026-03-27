
from pathlib import Path
from typing import Dict, List

class Map:
    pass

class MapManager:
    map_list: dict = {}
    def __init__(self) -> None:
        try:
            maps = self.get_all_maps()
            self.map_list = self.map_name_dict(maps)
        except Exception as e:
            raise ()
        
    def get_all_maps() -> list:
        maps = Path("maps").rglob("*.txt")
        map_list = sorted(list(maps))

        if not map_list:
            raise FileNotFoundError("Maps couldn't located.")

        # print(map_list)
        for i in map_list:
            print(i.parent.name)

        return map_list


    def map_name_dict(map_list: List[Path]) -> dict:
        map_dict: Dict = {}
        map_dict["easy"] = []
        map_dict["medium"] = []
        map_dict["hard"] = []
        map_dict["challenger"] = []

        for i in map_list:
            map_dict[i.parent.name].append(i)

        print(map_dict)

        map_dict_2: Dict = {}

        for i in map_list:
            splitted = i.stem.split("_", 1)
            map_dict_2[i.name] = {
                "name": splitted[1].replace("_", " ").title(),
                "category": i.parent.name,
                "number": splitted[0],
                "address": i
            }

        print(map_dict_2)


if __name__ == "__main__":
    maps = get_all_maps()
    map_name_dict(maps)
