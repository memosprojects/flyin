from pathlib import Path
from typing import Dict, List


class MapFolderManager:
    map_list: dict = {}

    def __init__(self) -> None:
        try:
            maps = self.get_all_maps()
            self.map_list = self.map_name_dict(maps)
        except Exception as e:
            raise RuntimeError(f"MapFolderManager initialization failed: {e}")

    def get_all_maps(self) -> list:
        try:
            maps_path = (
                Path(__file__).parent
                / ".."
                / "maps"
            ).resolve()

            if not maps_path.exists():
                raise FileNotFoundError(
                    f"Maps directory not found: {maps_path}")

            maps = maps_path.rglob("*.txt")
            map_list = sorted(list(maps))

            if not map_list:
                raise FileNotFoundError(
                    "No map files (.txt) found in maps directory.")

            return map_list

        except Exception as e:
            raise RuntimeError(f"Failed to load maps: {e}")

    def map_name_dict(self, map_list: List[Path]) -> dict:
        map_dict: Dict = {}

        for path in map_list:
            try:
                stem = path.stem
                splitted = stem.split("_", 1)

                if len(splitted) < 2:
                    raise ValueError(
                        f"Invalid map filename format: {path.name}")

                number, name_part = splitted

                map_dict[path.name] = {
                    "name": name_part.replace("_", " ").title(),
                    "category": path.parent.name,
                    "number": number,
                    "address": path
                }

            except Exception as e:
                print(f"Skipping invalid map file {path}: {e}")
                continue

        if not map_dict:
            raise RuntimeError("No valid maps could be parsed.")

        return map_dict
