from pathlib import Path
from .units import Hub, Connection
from typing import Any


class MapParser:
    '''Parse map files into structured data used by the planner.

    The parser validates syntax, extracts hubs, connections, metadata,
    and enforces constraints such as unique hubs and connections, and
    a single start/end hub.
    '''
    def __init__(self, file_path: Path):
        '''Initialize parser state.

        Args:
            file_path (Path): Path to the map file to parse.
        '''
        self.file_path = file_path
        self.hubs: dict[str, Hub] = {}
        self.connections: list = []
        self.drone_count: int = 0
        self._nb_drones_seen: bool = False
        self._seen_connections: set[tuple[str, str]] = set()

    def parse(self) -> dict[str, Any]:
        '''Parse the map file into a validated structure.

        Returns:
            dict[str, Any]: Dictionary with drone_count, hubs, and connections.

        Raises:
            ValueError: If the file is empty,
            malformed, or violates constraints.
        '''
        with open(self.file_path, "r") as file:
            lines = [
                (line_no, ln.strip())
                for line_no, ln in enumerate(file, start=1)
                if ln.strip() and not ln.strip().startswith("#")
            ]

        if not lines:
            raise ValueError("Map file is empty.")

        first_line_no, first_line = lines[0]
        if not first_line.startswith("nb_drones:"):
            raise ValueError(
                f"Line {first_line_no}: First meaningful line must be "
                "'nb_drones: <positive_integer>'."
            )

        self._parse_nb_drones(first_line, first_line_no)

        known_prefixes = (
            "hub:",
            "start_hub:",
            "end_hub:",
            "connection:",
            "nb_drones:",
        )

        for line_no, line in lines[1:]:
            if not line.startswith(known_prefixes):
                raise ValueError(
                    f"Line {line_no}: Unknown line prefix: '{line}'."
                )
            if line.startswith(("hub:", "start_hub:", "end_hub:")):
                self._process_line(line, line_no)
            elif line.startswith("connection:"):
                self._process_line_con(line, line_no)
            elif line.startswith("nb_drones:"):
                raise ValueError(
                    f"Line {line_no}: 'nb_drones' must appear exactly once."
                )

        self._make_connections()
        return self._finalize_map()

    def _parse_nb_drones(self, line: str, line_no: int) -> None:
        '''Parse and validate the 'nb_drones' declaration.

        Args:
            line (str): Raw line containing the declaration.
            line_no (int): Line number in the source file.

        Returns:
            None

        Raises:
            ValueError: If the declaration is malformed or invalid.
        '''
        if self._nb_drones_seen:
            raise ValueError(
                f"Line {line_no}: 'nb_drones' must appear exactly once."
            )

        prefix, separator, raw_value = line.partition(":")
        if prefix.strip() != "nb_drones" or separator != ":":
            raise ValueError(
                f"Line {line_no}: Malformed 'nb_drones' line. "
                "Expected 'nb_drones: <positive_integer>'."
            )

        value = raw_value.strip()
        if not value:
            raise ValueError(
                f"Line {line_no}: Malformed 'nb_drones' line. "
                "Missing drone count value."
            )

        try:
            drone_count = int(value)
        except ValueError as exc:
            raise ValueError(
                f"Line {line_no}: Malformed 'nb_drones' line. "
                "Drone count must be a positive integer."
            ) from exc

        if drone_count <= 0:
            raise ValueError(
                f"Line {line_no}: Malformed 'nb_drones' line. "
                "Drone count must be a positive integer."
            )

        self.drone_count = drone_count
        self._nb_drones_seen = True

    def _process_line(self, line: str, line_no: int) -> None:
        '''Process a hub-related line and register a Hub.

        Args:
            line (str): Raw hub line.
            line_no (int): Line number in the source file.

        Returns:
            None

        Raises:
            ValueError: If a duplicate hub is found or data is invalid.
        '''
        data = self._hub_data_extractor(line, line_no)
        h_type = data.pop("type")
        hub = Hub(
            is_start=(h_type == "start_hub"),
            is_end=(h_type == "end_hub"),
            **data  # name, x, y ve metadata verileri burada
        )
        if hub.name in self.hubs:
            raise ValueError(
                f"Line {line_no}: Duplicate hub name: '{hub.name}'."
            )
        self.hubs[hub.name] = hub

    def _process_line_con(self, line: str, line_no: int) -> None:
        '''Process a connection line and register a Connection.

        Args:
            line (str): Raw connection line.
            line_no (int): Line number in the source file.

        Returns:
            None

        Raises:
            ValueError: If hubs are undefined or connection is duplicate.
        '''
        data = self._con_data_extractor(line, line_no)

        source_name = data["source"]
        target_name = data["target"]
        edge_id = tuple(sorted((source_name, target_name)))

        if source_name not in self.hubs:
            raise ValueError(
                f"Line {line_no}: Connection error: Hub '{source_name}' "
                "not defined in map."
            )
        if target_name not in self.hubs:
            raise ValueError(
                f"Line {line_no}: Connection error: Hub '{target_name}' "
                "not defined in map."
            )
        if edge_id in self._seen_connections:
            raise ValueError(
                f"Line {line_no}: Duplicate connection: "
                f"'{source_name}-{target_name}'."
            )

        connection = Connection(
            source=self.hubs[source_name],
            target=self.hubs[target_name],
            max_link_capacity=data["max_link_capacity"]
        )
        self.connections.append(connection)
        self._seen_connections.add(edge_id)

    def _hub_data_extractor(self, line: str, line_no: int) -> dict:
        '''Extract hub fields and optional metadata from a line.

        Args:
            line (str): Raw hub line.
            line_no (int): Line number in the source file.

        Returns:
            dict: Parsed hub data
            including name, coordinates, type, and metadata.

        Raises:
            ValueError: If the format or metadata is malformed.
        '''
        prefix, _, raw_data = line.partition(":")
        prefix = prefix.strip()
        raw_data = raw_data.strip()

        metadata: dict[str, Any] = {}
        if "[" in raw_data or "]" in raw_data:
            start_idx = raw_data.find("[")
            end_idx = raw_data.find("]")
            if start_idx == -1 or end_idx == -1 or end_idx < start_idx:
                raise ValueError(
                    f"Line {line_no}: Malformed hub metadata: {line}"
                )
            if raw_data[end_idx + 1:].strip():
                raise ValueError(
                    f"Line {line_no}: Malformed hub metadata: {line}"
                )
            meta_str = raw_data[start_idx + 1: end_idx]
            metadata = self._parse_metadata(meta_str, line_no)
            raw_data = raw_data[:start_idx].strip()

        parts = raw_data.split()
        if len(parts) < 3:
            raise ValueError(f"Line {line_no}: Wrong Hub format: {line}")

        name, x, y = parts[0], parts[1], parts[2]

        hub_data = {
            "name": name,
            "x": x,
            "y": y,
            "type": prefix,
            **metadata
        }

        return hub_data

    def _parse_metadata(self, meta_str: str, line_no: int) -> dict[str, Any]:
        '''Parse key=value metadata inside brackets.

        Args:
            meta_str (str): Metadata string between brackets.
            line_no (int): Line number in the source file.

        Returns:
            dict[str, Any]: Parsed metadata with proper typing where possible.

        Raises:
            ValueError: If any token is malformed.
        '''
        metadata: dict[str, Any] = {}

        items = meta_str.split()
        if not items and meta_str.strip():
            raise ValueError(
                f"Line {line_no}: Malformed metadata: [{meta_str}]"
            )

        for item in items:
            if "=" not in item:
                raise ValueError(
                    f"Line {line_no}: Malformed metadata token: '{item}'."
                )

            key, raw_value = item.split("=", 1)
            key = key.strip()
            raw_value = raw_value.strip()

            if not key:
                raise ValueError(
                    f"Line {line_no}: Malformed metadata token: '{item}'."
                )
            if not raw_value:
                raise ValueError(
                    f"Line {line_no}: Malformed metadata token: '{item}'."
                )

            value: Any = raw_value
            if key == "zone":
                key = "zone_type"
            if raw_value.isdigit():
                value = int(raw_value)
            else:
                value = raw_value.strip("'\"")
                if not value:
                    raise ValueError(
                        f"Line {line_no}: Malformed metadata token: '{item}'."
                    )

            metadata[key] = value
        return metadata

    def _con_data_extractor(self, line: str, line_no: int) -> dict:
        '''Extract connection endpoints and optional metadata.

        Args:
            line (str): Raw connection line.
            line_no (int): Line number in the source file.

        Returns:
            dict: Parsed connection data with source, target, and capacity.

        Raises:
            ValueError: If the format or metadata is malformed.
        '''
        _, _, raw_data = line.partition(":")
        raw_data = raw_data.strip()

        metadata: dict[str, Any] = {}
        if "[" in raw_data or "]" in raw_data:
            start_idx = raw_data.find("[")
            end_idx = raw_data.find("]")
            if start_idx == -1 or end_idx == -1 or end_idx < start_idx:
                raise ValueError(
                    f"Line {line_no}: Malformed connection metadata: {line}"
                )
            if raw_data[end_idx + 1:].strip():
                raise ValueError(
                    f"Line {line_no}: Malformed connection metadata: {line}"
                )
            meta_str = raw_data[start_idx + 1: end_idx]
            metadata = self._parse_metadata(meta_str, line_no)
            raw_data = raw_data[:start_idx].strip()

        if raw_data.count("-") != 1:
            raise ValueError(
                f"Line {line_no}: Malformed connection format: '{line}'. "
                "Expected 'connection: <hub1>-<hub2>'."
            )

        source_name, target_name = raw_data.split("-", 1)
        source_name = source_name.strip()
        target_name = target_name.strip()

        if not source_name or not target_name:
            raise ValueError(
                f"Line {line_no}: Malformed connection format: '{line}'. "
                "Both source and target hub names are required."
            )

        return {
            "source": source_name,
            "target": target_name,
            "max_link_capacity": metadata.get("max_link_capacity", 1)
        }

    def _finalize_map(self) -> dict:
        '''Validate global constraints and build the final map dict.

        Returns:
            dict: Finalized map with drone_count, hubs, and connections.

        Raises:
            ValueError: If required elements (nb_drones, start, end)
            are missing or invalid.
        '''
        if not self._nb_drones_seen:
            raise ValueError("Map must define 'nb_drones' exactly once.")
        starts = [h for h in self.hubs.values() if h.is_start]
        ends = [h for h in self.hubs.values() if h.is_end]

        if len(starts) != 1:
            raise ValueError("Map must define exactly 1 start hub.")
        if len(ends) != 1:
            raise ValueError("Map must define exactly 1 end hub.")

        return {
            "drone_count": self.drone_count,
            "hubs": self.hubs,
            "connections": self.connections
            }

    def _make_connections(self) -> None:
        '''Populate neighbor lists for all hubs based on connections.

        Returns:
            None
        '''
        for conn in self.connections:
            if conn.target not in conn.source.neighbors:
                conn.source.neighbors.append(conn.target)
            if conn.source not in conn.target.neighbors:
                conn.target.neighbors.append(conn.source)
