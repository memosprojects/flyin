from pathlib import Path
from pydantic import BaseModel, Field, field_validator
from Units import Hub, Connection


class MapParser:
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.hubs: dict[str, Hub] = {}
        self.connections: list = []
        self.drone_count: int = 0

    def parse(self):
        with open(self.file_path, "r") as file:
            lines = [
                ln.strip() for ln in file
                if ln.strip() and not ln.startswith("#")
                ]

        for line in lines:
            if line.startswith(("hub:", "start_hub:", "end_hub:")):
                self._process_line(line)
            elif line.startswith("nb_drones"):
                self.drone_count = int(line.split(":")[1].strip())

        for line in lines:
            if line.startswith("connection:"):
                self._process_line_con(line)

        self._make_connections()

        return self._finalize_map()

    def _process_line(self, line: str):
        data = self._hub_data_extractor(line)
        h_type = data.pop("type")
        hub = Hub(
            is_start=(h_type == "start_hub"),
            is_end=(h_type == "end_hub"),
            **data  # name, x, y ve metadata verileri burada
        )
        self.hubs[hub.name] = hub

    def _process_line_con(self, line: str):
        data = self._con_data_extractor(line)

        try:
            connection = Connection(
                source=self.hubs[data["source"]],
                target=self.hubs[data["target"]],
                max_link_capacity=data["max_link_capacity"]
            )
            self.connections.append(connection)
        except KeyError as e:
            raise ValueError(f"Connection error: Hub '{e.args[0]}'"
                             " not defined in map.")

    def _hub_data_extractor(self, line: str) -> dict:
        prefix, _, raw_data = line.partition(":")
        prefix = prefix.strip()
        raw_data = raw_data.strip()

        metadata = {}
        if "[" in raw_data and "]" in raw_data:
            start_idx = raw_data.find("[")
            end_idx = raw_data.find("]")
            meta_str = raw_data[start_idx + 1: end_idx]
            metadata = self._parse_metadata(meta_str)
            raw_data = raw_data[:start_idx].strip()

        parts = raw_data.split()
        if len(parts) < 3:
            raise ValueError(f"Wrong Hub format: {line}")

        name, x, y = parts[0], parts[1], parts[2]

        hub_data = {
            "name": name,
            "x": x,
            "y": y,
            "type": prefix,
            **metadata
        }

        return hub_data

    def _parse_metadata(self, meta_str: str) -> dict:
        metadata = {}

        items = meta_str.split(" ")
        for i in items:
            if "=" in i:
                key, value = i.split("=", 1)
                if key == "zone":
                    key = "zone_type"
                if value.isdigit():
                    value = int(value)
                metadata[key] = value
        return metadata

    def _con_data_extractor(self, line: str) -> dict:
        _, _, raw_data = line.partition(":")
        raw_data = raw_data.strip()

        metadata = {}
        if "[" in line:
            start_idx = raw_data.find("[")
            meta_str = raw_data[start_idx + 1: raw_data.find("]")]
            metadata = self._parse_metadata(meta_str)
            raw_data = raw_data[:start_idx].strip()

        if "-" not in raw_data:
            raise ValueError(f"Invalid connection format (-): {line}")

        source_name, target_name = raw_data.split("-")

        return {
            "source": source_name.strip(),
            "target": target_name.strip(),
            "max_link_capacity": metadata.get("max_link_capacity", 1)
        }

    def _finalize_map(self):
        # En az bir start ve bir end hub var mı?
        starts = [h for h in self.hubs.values() if h.is_start]
        ends = [h for h in self.hubs.values() if h.is_end]

        if len(starts) != 1 or len(ends) != 1:
            raise ValueError("Map needs exactly 1 start and 1 end.")

        return {
            "drone_count": self.drone_count,
            "hubs": self.hubs,
            "connections": self.connections
            }

    def _make_connections(self):
        for conn in self.connections:
            if conn.target not in conn.source.neighbors:
                conn.source.neighbors.append(conn.target)
            if conn.source not in conn.target.neighbors:
                conn.target.neighbors.append(conn.source)


if __name__ == "__main__":
    # Test için bir harita dosyası yolu belirt (pathlib Path nesnesi)
    # Örn: maps/test_map.txt
    map_file = Path("maps/hard/03_ultimate_challenge.txt")

    if not map_file.exists():
        print(f"Hata: {map_file} bulunamadı. Lütfen geçerli bir dosya yolu verin.")
    else:
        parser = MapParser(map_file)

        try:
            # 1. Veriyi parse et
            parsed_data = parser.parse()

            # --- Sonucları Basalım ---
            print(f"{'='*10} MAP ANALYSIS: {map_file.name} {'='*10}")
            print(f"Drone Count: {parsed_data['drone_count']}")
            print(f"Total Hubs:  {len(parsed_data['hubs'])}")
            print(f"Total Conns: {len(parsed_data['connections'])}\n")

            print("--- HUB DETAILS ---")
            for name, hub in parsed_data['hubs'].items():
                # Hub bilgilerini ve komşularını yazdır
                status = "START" if hub.is_start else "END" if hub.is_end else "NORMAL"
                neighbor_names = [n.name for n in hub.neighbors]

                print(f"[{status}] {name:10} | Type: {hub.zone_type.value:10} | "
                      f"Cap: {hub.max_drones} | Neighbors: {neighbor_names}")

            print("\n--- CONNECTION DETAILS ---")
            for conn in parsed_data['connections']:
                print(f"Link: {conn.source.name} <-> {conn.target.name} | "
                      f"Link Cap: {conn.max_link_capacity}")

        except Exception as e:
            print(f"PARSING ERROR: {e}")
