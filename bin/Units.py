from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from dataclasses import dataclass, field


class ZoneType(Enum):
    '''Represent the traversal category of a hub.

    Each zone type affects whether a hub can be entered and how many
    turns are required to reach it.
    '''
    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"

    def cost(self) -> int:
        '''Return the traversal cost associated with the zone type.

        Returns:
            int: Number of turns required to enter this zone.

        Raises:
            ValueError: If the zone type does not define a valid cost.
        '''
        costs = {
            ZoneType.NORMAL: 1,
            ZoneType.PRIORITY: 1,
            ZoneType.RESTRICTED: 2,
        }

        if self not in costs:
            raise ValueError(f"Invalid ZoneType: {self.name}.")

        return costs[self]


class Hub(BaseModel):
    '''Store hub data and computed state helpers.

    A hub represents a zone in the map with coordinates, type,
    capacity, optional display color, and neighbor relationships.
    '''
    # Mandatory
    name: str
    x: int
    y: int

    # Values with default
    zone_type: ZoneType = ZoneType.NORMAL
    max_drones: int = Field(default=1, ge=1)
    color: Optional[str] = None
    is_start: bool = False
    is_end: bool = False
    neighbors: list["Hub"] = Field(default_factory=list)

    @property
    def cost(self) -> int:
        '''Return the movement cost of entering this hub.

        Returns:
            int: Number of turns required to enter the hub.
        '''
        return self.zone_type.cost()

    @property
    def is_blocked(self) -> bool:
        '''Check whether this hub is blocked.

        Returns:
            bool: True if the hub cannot be traversed.
        '''
        return self.zone_type == ZoneType.BLOCKED

    @property
    def is_priority(self) -> bool:
        '''Check whether this hub is a priority zone.

        Returns:
            bool: True if the hub is marked as priority.
        '''
        return self.zone_type == ZoneType.PRIORITY

    @property
    def is_restricted(self) -> bool:
        '''Check whether this hub is a restricted zone.

        Returns:
            bool: True if entering the hub requires two turns.
        '''
        return self.zone_type == ZoneType.RESTRICTED

    @property
    def is_traversable(self) -> bool:
        '''Check whether this hub can be entered.

        Returns:
            bool: True if the hub is not blocked.
        '''
        return self.zone_type != ZoneType.BLOCKED

    @field_validator("name")
    @classmethod
    def check_name_format(cls, v: str) -> str:
        '''Validate that the hub name does not contain forbidden characters.

        Args:
            v (str): Candidate hub name.

        Returns:
            str: Validated hub name.

        Raises:
            ValueError: If the hub name contains a hyphen.
        '''
        if "-" in v:
            raise ValueError(f"Invalid Hub name: '{v}'."
                             " '-' is forbidden in Hub names.")
        return v


class Connection(BaseModel):
    '''Represent a bidirectional link between two hubs.

    A connection stores its endpoints and the maximum number of drones
    that may traverse it simultaneously.
    '''
    source: Hub
    target: Hub
    max_link_capacity: int = Field(default=1, ge=1)

    @property
    def edge_id(self) -> tuple[str, str]:
        '''Return a normalized identifier for the connection.

        Returns:
            tuple[str, str]: Sorted hub name pair used as a unique edge key.
        '''
        first = self.source.name
        second = self.target.name
        if first <= second:
            return (first, second)
        return (second, first)

    def matches(self, a: str, b: str) -> bool:
        '''Check whether this connection links two given hub names.

        Args:
            a (str): First hub name.
            b (str): Second hub name.

        Returns:
            bool: True if the connection matches the given endpoints.
        '''
        return self.edge_id == tuple(sorted((a, b)))


@dataclass
class Drone:
    '''Store per-drone simulation state.

    Attributes:
        drone_id (int): Unique drone identifier.
        route (list[str]): Planned per-turn route states for the drone.
        current_turn (int): Current turn index used by the animation layer.
    '''
    drone_id: int
    route: list[str] = field(default_factory=list)
    current_turn: int = 0
