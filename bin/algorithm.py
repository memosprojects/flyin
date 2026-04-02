from __future__ import annotations

import heapq
import itertools
from dataclasses import dataclass
from typing import Any

from Units import Connection, Drone, Hub


@dataclass
class PlanResult:
    timeline: list[str]
    moves: list[tuple[str, str, int, int]]
    total_cost: int
    priority_visits: int


class DronePlanner:
    def __init__(self, parsed_data: dict[str, Any]):
        self.drone_count = parsed_data["drone_count"]
        self.hubs: dict[str, Hub] = parsed_data["hubs"]
        self.connections: list[Connection] = parsed_data["connections"]

        self.start_hub = self._find_start_hub()
        self.end_hub = self._find_end_hub()
        self.connection_map = self._build_connection_map()

        self.hub_usage: dict[int, dict[str, int]] = {}
        self.edge_usage: dict[int, dict[tuple[str, str], int]] = {}
        self.directed_edge_usage: dict[int, dict[tuple[str, str], int]] = {}

        self.drones: list[Drone] = [
            self._create_drone(drone_id=i)
            for i in range(1, self.drone_count + 1)
        ]

    def _create_drone(self, drone_id: int) -> Drone:
        try:
            drone = Drone(drone_id=drone_id)
        except TypeError:
            drone = Drone(drone_id)

        if not hasattr(drone, "route"):
            drone.route = []
        if not hasattr(drone, "current_turn"):
            drone.current_turn = 0

        return drone

    def _find_start_hub(self) -> Hub:
        for hub in self.hubs.values():
            if hub.is_start:
                return hub
        raise ValueError("Start hub not found.")

    def _find_end_hub(self) -> Hub:
        for hub in self.hubs.values():
            if hub.is_end:
                return hub
        raise ValueError("End hub not found.")

    def _build_connection_map(self) -> dict[tuple[str, str], Connection]:
        conn_map: dict[tuple[str, str], Connection] = {}

        for conn in self.connections:
            key = self._edge_key(conn.source.name, conn.target.name)
            conn_map[key] = conn

        return conn_map

    def _edge_key(self, a: str, b: str) -> tuple[str, str]:
        return tuple(sorted((a, b)))

    def _get_connection(self, a: str, b: str) -> Connection:
        key = self._edge_key(a, b)
        if key not in self.connection_map:
            raise ValueError(f"Connection not found between {a} and {b}.")
        return self.connection_map[key]

    def _zone_type_name(self, hub: Hub) -> str:
        zone = getattr(hub, "zone_type", "normal")
        if hasattr(zone, "value"):
            return str(zone.value).lower()
        return str(zone).lower()

    def _is_blocked(self, hub: Hub) -> bool:
        return self._zone_type_name(hub) == "blocked"

    def _is_priority(self, hub: Hub) -> bool:
        return self._zone_type_name(hub) == "priority"

    def _zone_move_cost(self, destination_hub: Hub) -> int:
        zone = self._zone_type_name(destination_hub)

        if zone == "blocked":
            raise ValueError(f"Blocked zone cannot be entered: {destination_hub.name}")
        if zone == "restricted":
            return 2
        return 1

    def _hub_capacity_ok(self, hub_name: str, turn: int) -> bool:
        hub = self.hubs[hub_name]

        if hub.is_start or hub.is_end:
            return True

        used = self.hub_usage.get(turn, {}).get(hub_name, 0)
        return used < int(hub.max_drones)

    def _edge_capacity_ok_for_interval(
        self,
        source_name: str,
        target_name: str,
        start_turn: int,
        duration: int,
    ) -> bool:
        conn = self._get_connection(source_name, target_name)
        edge_key = self._edge_key(source_name, target_name)
        reverse_key = (target_name, source_name)

        for used_turn in range(start_turn + 1, start_turn + duration + 1):
            used = self.edge_usage.get(used_turn, {}).get(edge_key, 0)
            if used >= int(conn.max_link_capacity):
                return False

            reverse_used = self.directed_edge_usage.get(
                used_turn,
                {},
            ).get(reverse_key, 0)
            if reverse_used > 0:
                return False

        return True

    def _can_wait(self, hub_name: str, next_turn: int) -> bool:
        return self._hub_capacity_ok(hub_name, next_turn)

    def _can_move(
        self,
        source_name: str,
        target_name: str,
        current_turn: int,
    ) -> tuple[bool, int]:
        target_hub = self.hubs[target_name]

        if self._is_blocked(target_hub):
            return False, current_turn

        duration = self._zone_move_cost(target_hub)
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

    def _generate_neighbors(
        self,
        hub_name: str,
        current_turn: int,
        max_turns: int,
    ) -> list[tuple[int, int, tuple[str, int], list[str], Any]]:
        neighbors_data: list[tuple[int, int, tuple[str, int], list[str], Any]] = []

        next_turn = current_turn + 1
        if next_turn <= max_turns and self._can_wait(hub_name, next_turn):
            neighbors_data.append(
                (
                    1,
                    0,
                    (hub_name, next_turn),
                    [hub_name],
                    None,
                )
            )

        current_hub = self.hubs[hub_name]
        for neighbor in current_hub.neighbors:
            if self._is_blocked(neighbor):
                continue

            allowed, arrival_turn = self._can_move(
                hub_name,
                neighbor.name,
                current_turn,
            )
            if not allowed or arrival_turn > max_turns:
                continue

            duration = arrival_turn - current_turn
            priority_gain = 1 if self._is_priority(neighbor) else 0

            if duration == 1:
                segment = [neighbor.name]
            else:
                segment = [f"{hub_name}->{neighbor.name}", neighbor.name]

            move_record = (
                hub_name,
                neighbor.name,
                current_turn,
                duration,
            )

            neighbors_data.append(
                (
                    duration,
                    priority_gain,
                    (neighbor.name, arrival_turn),
                    segment,
                    move_record,
                )
            )

        return neighbors_data

    def _reconstruct_plan(
        self,
        parent: dict[tuple[str, int], tuple[str, int]],
        segment_map: dict[tuple[str, int], list[str]],
        move_map: dict[tuple[str, int], Any],
        end_state: tuple[str, int],
        total_cost: int,
        priority_visits: int,
    ) -> PlanResult:
        segments: list[list[str]] = []
        moves: list[tuple[str, str, int, int]] = []

        current = end_state
        while current in parent:
            segments.append(segment_map[current])

            move_record = move_map[current]
            if move_record is not None:
                moves.append(move_record)

            current = parent[current]

        start_hub_name, _start_turn = current

        timeline = [start_hub_name]
        for segment in reversed(segments):
            timeline.extend(segment)

        moves.reverse()

        return PlanResult(
            timeline=timeline,
            moves=moves,
            total_cost=total_cost,
            priority_visits=priority_visits,
        )

    def _reserve_plan(self, plan: PlanResult) -> None:
        for turn, state in enumerate(plan.timeline):
            if "->" in state:
                continue

            hub_name = state
            hub = self.hubs[hub_name]

            if hub.is_start or hub.is_end:
                continue

            self.hub_usage.setdefault(turn, {})
            self.hub_usage[turn][hub_name] = (
                self.hub_usage[turn].get(hub_name, 0) + 1
            )

        for source_name, target_name, start_turn, duration in plan.moves:
            edge_key = self._edge_key(source_name, target_name)
            directed_key = (source_name, target_name)

            for used_turn in range(start_turn + 1, start_turn + duration + 1):
                self.edge_usage.setdefault(used_turn, {})
                self.edge_usage[used_turn][edge_key] = (
                    self.edge_usage[used_turn].get(edge_key, 0) + 1
                )

                self.directed_edge_usage.setdefault(used_turn, {})
                self.directed_edge_usage[used_turn][directed_key] = (
                    self.directed_edge_usage[used_turn].get(directed_key, 0) + 1
                )

    def plan_single_drone(self, max_turns: int = 200) -> PlanResult:
        start_state = (self.start_hub.name, 0)

        parent: dict[tuple[str, int], tuple[str, int]] = {}
        segment_map: dict[tuple[str, int], list[str]] = {}
        move_map: dict[tuple[str, int], Any] = {}

        best_score: dict[tuple[str, int], tuple[int, int]] = {
            start_state: (0, 0)
        }

        counter = itertools.count()
        heap: list[tuple[int, int, int, tuple[str, int], int]] = []
        heapq.heappush(
            heap,
            (0, 0, next(counter), start_state, 0),
        )

        while heap:
            total_cost, neg_priority, _idx, state, priority_visits = heapq.heappop(
                heap,
            )

            if best_score.get(state) != (total_cost, neg_priority):
                continue

            hub_name, current_turn = state

            if hub_name == self.end_hub.name:
                return self._reconstruct_plan(
                    parent=parent,
                    segment_map=segment_map,
                    move_map=move_map,
                    end_state=state,
                    total_cost=total_cost,
                    priority_visits=priority_visits,
                )

            for neighbor_data in self._generate_neighbors(
                hub_name,
                current_turn,
                max_turns,
            ):
                move_cost, priority_gain, next_state, segment, move_record = (
                    neighbor_data
                )

                next_total_cost = total_cost + move_cost
                next_priority_visits = priority_visits + priority_gain
                next_neg_priority = -next_priority_visits

                current_best = best_score.get(next_state)
                candidate_score = (next_total_cost, next_neg_priority)

                if current_best is not None and candidate_score >= current_best:
                    continue

                best_score[next_state] = candidate_score
                parent[next_state] = state
                segment_map[next_state] = segment
                move_map[next_state] = move_record

                heapq.heappush(
                    heap,
                    (
                        next_total_cost,
                        next_neg_priority,
                        next(counter),
                        next_state,
                        next_priority_visits,
                    ),
                )

        raise ValueError("No valid route found for drone within turn limit.")

    def plan_all_drones(self, max_turns: int = 200) -> list[Drone]:
        for drone in self.drones:
            plan = self.plan_single_drone(max_turns=max_turns)
            drone.route = plan.timeline
            drone.current_turn = 0

            if hasattr(drone, "delivery_turn"):
                drone.delivery_turn = len(plan.timeline) - 1

            self._reserve_plan(plan)

        return self.drones

    def print_turns(self) -> None:
        if not self.drones:
            return

        max_len = max(len(drone.route) for drone in self.drones)

        for turn in range(max_len):
            print(f"TURN {turn}")
            for drone in self.drones:
                if turn < len(drone.route):
                    print(f"  Drone {drone.drone_id}: {drone.route[turn]}")
            print()


if __name__ == "__main__":
    from pathlib import Path
    from parser import MapParser

    map_file = Path("/home/mehdemir/Projects/Fly/maps/challenger/01_the_impossible_dream.txt")

    parser = MapParser(map_file)
    parsed_data = parser.parse()

    planner = DronePlanner(parsed_data)
    drones = planner.plan_all_drones(max_turns=200)

    for drone in drones:
        print(f"Drone {drone.drone_id}: {' | '.join(drone.route)}")

    planner.print_turns()
