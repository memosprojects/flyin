from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


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

    def is_traversable(self) -> bool:
        """Bölgenin üzerinden geçilip geçilemeyeceğini belirler."""
        return self != ZoneType.BLOCKED


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

    @field_validator("name")
    @classmethod
    def check_name_format(cls, v: str) -> str:
        """Yönerge gereği bölge isimlerinde tire (-) bulunamaz."""
        if "-" in v:
            raise ValueError(f"Invalid Hub name: '{v}'."
                             " '-' is forbidden in Hub names.")
        return v


class Connection(BaseModel):
    source: Hub
    target: Hub
    max_link_capacity: int = Field(default=1, ge=1)

