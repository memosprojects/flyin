from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from Units import Drone, Hub, Connection


@dataclass
class PlanResult:
    timeline: list[str]
    moves: list[tuple[str, str, int, int]]
    total_cost: int


# Type aliases for state and move representations
State = tuple[str, int, str | None]
Move = tuple[str, str, int, int]


class DronePlanner:
    def __init__(self, parsed_data: dict[str, Any]):
        '''Initialize the DronePlanner.

        Args:
            parsed_data (dict[str, Any]):
            Parsed map data including hubs, connections, and drone count.
        '''
        self.parsed_data = parsed_data

        self.drone_count: int = parsed_data["drone_count"]
        self.hubs: dict[str, Hub] = parsed_data["hubs"]
        self.connections: list[Connection] = parsed_data["connections"]

        self.start_hub: Hub = self._find_start_hub()
        self.end_hub: Hub = self._find_end_hub()

        self.connection_map: dict[
            tuple[str, str], Connection
            ] = self._build_connection_map()

        self.hub_usage: dict[int, dict[str, int]] = {}
        self.edge_usage: dict[int, dict[tuple[str, str], int]] = {}

        self.drones: list[Drone] = self._create_drones()
        self.debug: bool = True

    def _find_start_hub(self) -> Hub:
        '''Find the start hub in the map.

        Returns:
            Hub: The hub marked as start.

        Raises:
            ValueError: If no start hub is found.
        '''
        for hub in self.hubs.values():
            if hub.is_start:
                return hub
        raise ValueError("Start hub not found.")

    def _find_end_hub(self) -> Hub:
        '''Find the end hub in the map.

        Returns:
            Hub: The hub marked as end.

        Raises:
            ValueError: If no end hub is found.
        '''
        for hub in self.hubs.values():
            if hub.is_end:
                return hub
        raise ValueError("End hub not found.")

    def _build_connection_map(self) -> dict[tuple[str, str], Connection]:
        '''Create a lookup map for connections.

        Returns:
            dict[tuple[str, str], Connection]:
            Mapping of edge IDs to connection objects.
        '''
        connection_map: dict[tuple[str, str], Connection] = {}

        for conn in self.connections:
            connection_map[conn.edge_id] = conn

        return connection_map

    def _create_drones(self) -> list[Drone]:
        '''Create drone instances for the simulation.

        Returns:
            list[Drone]: List of initialized drones.
        '''
        drones: list[Drone] = []

        for drone_id in range(1, self.drone_count + 1):
            drone = Drone(drone_id=drone_id)
            drone.route = []
            drone.current_turn = 0
            drones.append(drone)

        return drones

    def _get_connection(self, a: str, b: str) -> Connection:
        '''Retrieve a connection between two hubs.

        Args:
            a (str): Source hub name.
            b (str): Target hub name.

        Returns:
            Connection: Connection object between hubs.

        Raises:
            ValueError: If connection does not exist.
        '''
        edge_id: tuple[str, str] = tuple(sorted((a, b)))  # type: ignore

        if edge_id not in self.connection_map:
            raise ValueError(f"Connection not found between {a} and {b}.")

        return self.connection_map[edge_id]

    def _get_connection_label(self, a: str, b: str) -> str:
        '''Get a printable label for a connection.

        Args:
            a (str): Source hub name.
            b (str): Target hub name.

        Returns:
            str: Human-readable connection label.
        '''
        conn = self._get_connection(a, b)

        if hasattr(conn, "name"):
            conn_name = getattr(conn, "name")
            if isinstance(conn_name, str) and conn_name:
                return conn_name

        if hasattr(conn, "label"):
            conn_label = getattr(conn, "label")
            if isinstance(conn_label, str) and conn_label:
                return conn_label

        return f"{a}->{b}"

    def _hub_capacity_ok(self, hub_name: str, turn: int) -> bool:
        '''Check if a hub has available capacity.

        Args:
            hub_name (str): Name of the hub.
            turn (int): Simulation turn.

        Returns:
            bool: True if capacity allows entry, False otherwise.
        '''
        hub = self.hubs[hub_name]

        if hub.is_start or hub.is_end:
            return True

        used: int = self.hub_usage.get(turn, {}).get(hub_name, 0)
        return used < int(hub.max_drones)

    def _can_wait(self, hub_name: str, next_turn: int) -> bool:
        '''Check if a drone can wait at a hub.

        Args:
            hub_name (str): Name of the hub.
            next_turn (int): Next simulation turn.

        Returns:
            bool: True if waiting is allowed.
        '''
        return self._hub_capacity_ok(hub_name, next_turn)

    def _edge_capacity_ok_for_interval(
        self,
        source_name: str,
        target_name: str,
        start_turn: int,
        duration: int,
    ) -> bool:
        '''Check edge capacity across a time interval.

        Args:
            source_name (str): Source hub.
            target_name (str): Target hub.
            start_turn (int): Starting turn.
            duration (int): Travel duration.

        Returns:
            bool: True if edge capacity is sufficient.
        '''
        conn = self._get_connection(source_name, target_name)
        edge_id = conn.edge_id

        for used_turn in range(start_turn + 1, start_turn + duration + 1):
            used: int = self.edge_usage.get(used_turn, {}).get(edge_id, 0)

            if used >= conn.max_link_capacity:
                return False

        return True

    def _can_move(
        self,
        source_name: str,
        target_name: str,
        current_turn: int,
    ) -> tuple[bool, int]:
        '''Check if a drone can move to a target hub.

        Args:
            source_name (str): Current hub.
            target_name (str): Destination hub.
            current_turn (int): Current turn.

        Returns:
            tuple[bool, int]: (allowed, arrival_turn).
        '''
        target_hub = self.hubs[target_name]

        if target_hub.is_blocked:
            return False, current_turn

        duration = target_hub.cost
        arrival_turn = current_turn + duration

        if not self._edge_capacity_ok_for_interval(
            source_name,
            target_name,
            current_turn,
            duration,
        ):
            return False, current_turn

        if not self._hub_capacity_ok(target_name, arrival_turn):
            return False, current_turn

        return True, arrival_turn

    def get_neighbors(
        self,
        hub_name: str,
        current_turn: int,
        previous_hub: str | None,
    ) -> list[tuple[int, int, State, list[str], Move | None]]:
        '''Generate valid next states from current state.

        Args:
            hub_name (str): Current hub.
            current_turn (int): Current turn.
            previous_hub (str | None): Previously visited hub.

        Returns:
            list: List of neighbor state transitions.
        '''
        neighbors: list[tuple[int, int, State, list[str], Move | None]] = []

        next_turn = current_turn + 1
        if self._can_wait(hub_name, next_turn):
            neighbors.append(
                (
                    1,
                    0,
                    (hub_name, next_turn, previous_hub),
                    [hub_name],
                    None,
                )
            )

        current_hub = self.hubs[hub_name]

        for neighbor in current_hub.neighbors:
            if neighbor.is_blocked:
                continue

            if previous_hub is not None and neighbor.name == previous_hub:
                continue

            allowed, arrival_turn = self._can_move(
                hub_name,
                neighbor.name,
                current_turn,
            )
            if not allowed:
                continue

            duration = arrival_turn - current_turn
            priority_gain = 1 if neighbor.is_priority else 0
            conn_label = self._get_connection_label(hub_name, neighbor.name)

            if duration == 1:
                segment = [neighbor.name]
            else:
                segment = [conn_label, neighbor.name]

            move_record: Move = (
                hub_name,
                neighbor.name,
                current_turn,
                duration,
            )

            next_state: State = (
                neighbor.name,
                arrival_turn,
                hub_name,
            )

            neighbors.append(
                (
                    duration,
                    priority_gain,
                    next_state,
                    segment,
                    move_record,
                )
            )

        return neighbors

    def plan_to_target(
        self,
        start_hub_name: str,
        start_turn: int,
        previous_hub: str | None,
        target_hub_name: str,
    ) -> PlanResult:
        '''Compute a route to the target hub.

        Args:
            start_hub_name (str): Starting hub.
            start_turn (int): Initial turn.
            previous_hub (str | None): Previous hub.
            target_hub_name (str): Destination hub.

        Returns:
            PlanResult: Computed plan including timeline and moves.

        Raises:
            ValueError: If no path is found.
        '''
        start_state: State = (start_hub_name, start_turn, previous_hub)

        open_states: list[State] = [start_state]
        best_score: dict[State, tuple[int, int]] = {start_state: (0, 0)}
        priority_count: dict[State, int] = {start_state: 0}

        parent: dict[State, State] = {}
        segment_map: dict[State, list[str]] = {}
        move_map: dict[State, Move | None] = {}

        while open_states:
            current_state = min(open_states,
                                key=lambda state: best_score[state])
            open_states.remove(current_state)

            hub_name, current_turn, prev_hub = current_state
            current_cost, _ = best_score[current_state]
            current_priority_visits = priority_count[current_state]

            if hub_name == target_hub_name:
                return self._reconstruct_plan(
                    current_state,
                    current_cost,
                    parent,
                    segment_map,
                    move_map,
                )

            neighbors = self.get_neighbors(
                hub_name,
                current_turn,
                prev_hub,
            )

            for mv_cst, prio_gain, next_state, segment, mv_record in neighbors:
                next_total_cost = current_cost + mv_cst
                next_priority_visits = current_priority_visits + prio_gain
                next_score = (next_total_cost, -next_priority_visits)

                current_best = best_score.get(next_state)
                if current_best is not None and next_score >= current_best:
                    continue

                best_score[next_state] = next_score
                priority_count[next_state] = next_priority_visits
                parent[next_state] = current_state
                segment_map[next_state] = segment
                move_map[next_state] = mv_record

                if next_state not in open_states:
                    open_states.append(next_state)

        raise ValueError(f"No valid path found to {target_hub_name}.")

    def _reconstruct_plan(
        self,
        end_state: State,
        total_cost: int,
        parent: dict[State, State],
        segment_map: dict[State, list[str]],
        move_map: dict[State, Move | None],
    ) -> PlanResult:
        '''Reconstruct plan from search results.

        Args:
            end_state (State): Final state.
            total_cost (int): Total path cost.
            parent (dict): Parent mapping.
            segment_map (dict): Segment mapping.
            move_map (dict): Move mapping.

        Returns:
            PlanResult: Reconstructed plan.
        '''
        segments: list[list[str]] = []
        moves: list[Move] = []

        current_state: State | None = end_state

        while current_state in parent:
            segments.append(segment_map[current_state])

            move_record = move_map[current_state]
            if move_record is not None:
                moves.append(move_record)

            current_state = parent[current_state]

        start_hub_name = current_state[0] if current_state else ""

        timeline: list[str] = [start_hub_name]

        for segment in reversed(segments):
            timeline.extend(segment)

        moves.reverse()

        return PlanResult(
            timeline=timeline,
            moves=moves,
            total_cost=total_cost,
        )

    def _reserve_plan(self, plan: PlanResult) -> None:
        '''Reserve resources for a planned route.

        Args:
            plan (PlanResult): Plan to reserve.
        '''
        for turn, state in enumerate(plan.timeline):
            if "->" in state:
                continue

            hub_name = state
            hub = self.hubs[hub_name]

            if hub.is_start or hub.is_end:
                continue

            if turn not in self.hub_usage:
                self.hub_usage[turn] = {}

            if hub_name not in self.hub_usage[turn]:
                self.hub_usage[turn][hub_name] = 0

            self.hub_usage[turn][hub_name] += 1

        for source_name, target_name, start_turn, duration in plan.moves:
            conn = self._get_connection(source_name, target_name)
            edge_id = conn.edge_id

            for used_turn in range(start_turn + 1, start_turn + duration + 1):
                if used_turn not in self.edge_usage:
                    self.edge_usage[used_turn] = {}

                if edge_id not in self.edge_usage[used_turn]:
                    self.edge_usage[used_turn][edge_id] = 0

                self.edge_usage[used_turn][edge_id] += 1

    def plan_all_drones(self) -> list[Drone]:
        '''Plan routes for all drones.

        Returns:
            list[Drone]: Drones with assigned routes.
        '''
        for drone in self.drones:
            plan = self.plan_to_target(
                self.start_hub.name,
                0,
                None,
                self.end_hub.name,
            )

            drone.route = plan.timeline
            drone.current_turn = 0

            self._reserve_plan(plan)

        return self.drones

    def print_simulation(self) -> None:
        '''Print simulation results turn by turn.

        Returns:
            None
        '''
        if not self.drones:
            return

        active_drones = {drone.drone_id: drone for drone in self.drones}
        max_len = max(len(drone.route) for drone in self.drones)

        for turn in range(1, max_len):
            movements = []
            delivered_this_turn = []

            for drone_id, drone in list(active_drones.items()):
                if turn >= len(drone.route):
                    continue

                previous_state = drone.route[turn - 1]
                current_state = drone.route[turn]

                if current_state == previous_state:
                    continue

                movements.append(f"D{drone.drone_id}-{current_state}")

                if current_state == self.end_hub.name:
                    delivered_this_turn.append(drone_id)

            if movements:
                print(" ".join(movements))

            for drone_id in delivered_this_turn:
                del active_drones[drone_id]

            if not active_drones:
                break
