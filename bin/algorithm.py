from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from Units import Connection, Drone, Hub
from parser import MapParser
from dataclasses import dataclass


@dataclass
class PlanResult:
    timeline: list[str]
    moves: list[tuple[str, str, int, int]]
    total_cost: int


class DronePlanner:
    def __init__(self, parsed_data: dict):
        self.parsed_data = parsed_data

        self.drone_count = parsed_data["drone_count"]
        self.hubs = parsed_data["hubs"]
        self.connections = parsed_data["connections"]

        self.start_hub = self._find_start_hub()
        self.end_hub = self._find_end_hub()

        self.connection_map = self._build_connection_map()

        self.hub_usage = {}
        self.edge_usage = {}

        self.drones = self._create_drones()
        self.debug = True

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

    def _build_connection_map(self) -> dict:
        connection_map = {}

        for conn in self.connections:
            connection_map[conn.edge_id] = conn

        return connection_map

    def _create_drones(self) -> list:
        drones = []

        for drone_id in range(1, self.drone_count + 1):
            drone = Drone(drone_id=drone_id)
            drone.route = []
            drone.current_turn = 0
            drones.append(drone)

        return drones

    def _get_connection(self, a: str, b: str):
        edge_id = tuple(sorted((a, b)))

        if edge_id not in self.connection_map:
            raise ValueError(f"Connection not found between {a} and {b}.")

        return self.connection_map[edge_id]

    def _hub_capacity_ok(self, hub_name: str, turn: int) -> bool:
        hub = self.hubs[hub_name]

        if hub.is_start or hub.is_end:
            return True

        used = self.hub_usage.get(turn, {}).get(hub_name, 0)
        return used < hub.max_drones

    def _can_wait(self, hub_name: str, next_turn: int) -> bool:
        return self._hub_capacity_ok(hub_name, next_turn)

    def _edge_capacity_ok_for_interval(
        self,
        source_name: str,
        target_name: str,
        start_turn: int,
        duration: int,
    ) -> bool:
        conn = self._get_connection(source_name, target_name)
        edge_id = conn.edge_id

        for used_turn in range(start_turn + 1, start_turn + duration + 1):
            used = self.edge_usage.get(used_turn, {}).get(edge_id, 0)

            if used >= conn.max_link_capacity:
                return False

        return True

    def _can_move(
        self,
        source_name: str,
        target_name: str,
        current_turn: int,
    ) -> tuple[bool, int]:
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
    ):
        neighbors = []

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

            next_state = (
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
        start_state = (start_hub_name, start_turn, previous_hub)

        open_states = [start_state]
        best_score = {start_state: (0, 0)}
        priority_count = {start_state: 0}

        parent = {}
        segment_map = {}
        move_map = {}

        while open_states:
            current_state = min(open_states, key=lambda state: best_score[state])
            open_states.remove(current_state)

            hub_name, current_turn, prev_hub = current_state
            current_cost, current_neg_priority = best_score[current_state]
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

            for move_cost, priority_gain, next_state, segment, move_record in neighbors:
                next_total_cost = current_cost + move_cost
                next_priority_visits = current_priority_visits + priority_gain
                next_score = (next_total_cost, -next_priority_visits)

                current_best = best_score.get(next_state)
                if current_best is not None and next_score >= current_best:
                    continue

                best_score[next_state] = next_score
                priority_count[next_state] = next_priority_visits
                parent[next_state] = current_state
                segment_map[next_state] = segment
                move_map[next_state] = move_record

                if next_state not in open_states:
                    open_states.append(next_state)

        raise ValueError(f"No valid path found to {target_hub_name}.")

    def _reconstruct_plan(
        self,
        end_state,
        total_cost,
        parent,
        segment_map,
        move_map,
    ):
        segments = []
        moves = []

        current_state = end_state

        while current_state in parent:
            segments.append(segment_map[current_state])

            move_record = move_map[current_state]
            if move_record is not None:
                moves.append(move_record)

            current_state = parent[current_state]

        start_hub_name, _start_turn, _prev_hub = current_state

        timeline = [start_hub_name]

        for segment in reversed(segments):
            timeline.extend(segment)

        moves.reverse()

        return PlanResult(
            timeline=timeline,
            moves=moves,
            total_cost=total_cost,
        )

    def _reserve_plan(self, plan: PlanResult):
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
    
    def print_solution(self) -> None:
        if not self.drones:
            print("No drones planned.")
            return

        max_len = max(len(drone.route) for drone in self.drones)

        print("=== SOLUTION ===")
        print()

        for drone in self.drones:
            route_text = " | ".join(drone.route)
            print(f"Drone {drone.drone_id}: {route_text}")

        print()
        print("=== TURN BY TURN ===")
        print()

        for turn in range(max_len):
            print(f"TURN {turn}")
            for drone in self.drones:
                if turn < len(drone.route):
                    print(f"  Drone {drone.drone_id}: {drone.route[turn]}")
            print()


if __name__ == "__main__":
    parser = MapParser("/home/mehdemir/Projects/Fly/maps/challenger/01_the_impossible_dream.txt")
    parsed_data = parser.parse()
    planner = DronePlanner(parsed_data)
    planner.plan_all_drones()
    planner.print_solution()

