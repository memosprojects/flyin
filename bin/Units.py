from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator, computed_field
from dataclasses import dataclass, field


class ZoneType(Enum):
    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"

    def cost(self) -> int:
        costs = {
            ZoneType.NORMAL: 1,
            ZoneType.PRIORITY: 1,
            ZoneType.RESTRICTED: 2,
        }

        if self not in costs:
            raise ValueError(f"Invalid ZoneType: {self.name}.")

        return costs[self]


class Hub(BaseModel):
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
        return self.zone_type.cost()

    @property
    def is_blocked(self) -> bool:
        return self.zone_type == ZoneType.BLOCKED

    @property
    def is_priority(self) -> bool:
        return self.zone_type == ZoneType.PRIORITY

    @property
    def is_restricted(self) -> bool:
        return self.zone_type == ZoneType.RESTRICTED

    @property
    def is_traversable(self) -> bool:
        return self.zone_type != ZoneType.BLOCKED

    @field_validator("name")
    @classmethod
    def check_name_format(cls, v: str) -> str:
        if "-" in v:
            raise ValueError(f"Invalid Hub name: '{v}'."
                             " '-' is forbidden in Hub names.")
        return v


class Connection(BaseModel):
    source: Hub
    target: Hub
    max_link_capacity: int = Field(default=1, ge=1)

    @computed_field
    @property
    def edge_id(self) -> tuple[str, str]:
        return tuple(sorted((self.source.name, self.target.name)))

    def matches(self, a: str, b: str) -> bool:
        return self.edge_id == tuple(sorted((a, b)))


@dataclass
class Drone:
    drone_id: int
    route: list[str] = field(default_factory=list)
    current_turn: int = 0
