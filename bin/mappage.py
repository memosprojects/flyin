import arcade
import arcade.gui
from pathlib import Path
import math
from typing import Any, Dict, List, Tuple, Optional

from parser import MapParser
from algorithm import DronePlanner
from Units import Drone, Hub, Connection


class MapView(arcade.View):
    def __init__(self, map_path: str, map_name: str) -> None:
        super().__init__()

        self.map_path: Path = Path(map_path)
        self.map_name: str = map_name

        self.ui: arcade.gui.UIManager = arcade.gui.UIManager()
        self.background: arcade.Texture = arcade.load_texture(
            Path(__file__).parent
            / ".."
            / "uilibrary"
            / "background.jpeg"
        )
        self.anchor: arcade.gui.UIAnchorLayout = arcade.gui.UIAnchorLayout()

        self.parsed_data: Optional[Dict[str, Any]] = None
        self.hubs: Dict[str, Hub] = {}
        self.connections: List[Connection] = []
        self.drone_count: int = 0

        self.margin: int = 80
        self.scale: float = 1.0

        self.text_objects: Dict[str, Any] = {}

        self.load_textures()

        # Animation assets
        self.current_turn: int = 0
        self.target_turn: int = 0

        self.turn_animating: bool = False
        self.turn_progress: float = 0.0
        self.turn_animation_duration: float = 0.6

        self.drones: List[Drone] = []
        self.drone_sprites: arcade.SpriteList = arcade.SpriteList()
        self.drone_sprite_map: Dict[int, arcade.Sprite] = {}
        self.turn_label: Optional[arcade.gui.UILabel] = None

        self.max_turn: int = self.get_finished_turn()

        # Late-initialized attributes
        self.min_x: int = 0
        self.max_x: int = 0
        self.min_y: int = 0
        self.max_y: int = 0
        self.offset_x: float = 0.0
        self.offset_y: float = 0.0
        self.hub_screen_positions: Dict[str, Tuple[float, float]] = {}
        self.start_hub: Hub
        self.hub_sprites: arcade.SpriteList = arcade.SpriteList()
        self.hub_markers: arcade.SpriteList = arcade.SpriteList()
        self.hub_name_texts: List[arcade.Text] = []

    def load_textures(self) -> None:
        islandsheet = arcade.load_spritesheet(
            Path(__file__).parent
            / ".."
            / "uilibrary"
            / "Island.png"
        )

        self.island: arcade.Texture = islandsheet.get_texture(
            rect=arcade.LBWH(0, 1, 47, 71)
        )

    def get_hub_scale(self) -> float:
        return self.get_hub_display_size() / self.island.width

    def on_show_view(self) -> None:
        self.ui.enable()
        self.ui.add(self.anchor)

        back_button = arcade.gui.UIFlatButton(
            text="Back",
            width=120,
        )
        back_button.on_click = self.go_back  # type: ignore[method-assign]

        next_button = arcade.gui.UIFlatButton(
            text="Next Turn",
            width=140,
        )
        next_button.on_click = self.on_next_turn  # type: ignore[method-assign]

        quit_button = arcade.gui.UIFlatButton(
            text="Quit",
            width=120,
        )
        quit_button.on_click = self.quit_game  # type: ignore[method-assign]

        self.load_map()
        self.setup_texts()

        self.turn_label = arcade.gui.UILabel(
            text=f"TURN {self.current_turn} / {self.max_turn}",
            font_size=16,
            text_color=arcade.color.WHITE,
        )

        bottom_box = arcade.gui.UIBoxLayout(
            vertical=False,
            space_between=10
        )
        if self.turn_label:
            bottom_box.add(self.turn_label)
        bottom_box.add(next_button)

        self.anchor.add(
            child=bottom_box,
            anchor_x="right",
            anchor_y="bottom",
            align_x=-20,
            align_y=20,
        )

        self.anchor.add(
            child=back_button,
            anchor_x="left",
            anchor_y="top",
            align_x=20,
            align_y=-20,
        )

        self.anchor.add(
            child=quit_button,
            anchor_x="right",
            anchor_y="top",
            align_x=-20,
            align_y=-20,
        )

    def quit_game(self, event: arcade.gui.UIOnClickEvent) -> None:
        arcade.exit()

    def on_hide_view(self) -> None:
        self.ui.disable()

    def load_map(self) -> None:
        parser = MapParser(self.map_path)
        self.parsed_data = parser.parse()

        # Type guard for mypy indexing
        if self.parsed_data is not None:
            self.drone_count = self.parsed_data["drone_count"]
            self.hubs = self.parsed_data["hubs"]
            self.connections = self.parsed_data["connections"]

            planner = DronePlanner(self.parsed_data)
            self.drones = planner.plan_all_drones()
            self.max_turn = self.get_finished_turn()
            planner.print_simulation()

        self.start_hub = next(
            hub for hub in self.hubs.values() if hub.is_start
        )

        self.compute_scale()

        self.hub_screen_positions = {}
        for name, hub in self.hubs.items():
            self.hub_screen_positions[name] = self.transform_position(
                hub.x, hub.y
            )

        self.build_hub_sprites()
        self.build_drone_sprites()
        self.refresh_turn_label()
        self.update_drone_positions_static()

    def setup_texts(self) -> None:
        self.text_objects["map"] = arcade.Text(
            f"MAP: {self.map_name}",
            160,
            self.window.height - 35,
            arcade.color.WHITE,
            18,
            bold=True,
        )

        self.text_objects["drones"] = arcade.Text(
            f"Drones: {self.drone_count}",
            160,
            self.window.height - 65,
            arcade.color.LIGHT_GRAY,
            14,
        )

        self.text_objects["stats"] = arcade.Text(
            f"Hubs: {len(self.hubs)} | "
            f"Connections: {len(self.connections)}",
            160,
            self.window.height - 90,
            arcade.color.LIGHT_GRAY,
            14,
        )

        self.text_objects["hub_capacity"] = []
        self.text_objects["hub_zone"] = []

    def get_color_from_string(self, color_str: str) -> Any:
        if not color_str:
            return None

        color_str = color_str.upper().strip()
        if color_str.startswith("#"):
            try:
                # Fix: arcade uses color_from_hex_string
                return arcade.color_from_hex_string(color_str)
            except (ValueError, AttributeError):
                return arcade.color.GRAY
        try:
            return getattr(arcade.color, color_str)
        except AttributeError:
            return arcade.color.GRAY

    def get_hub_color(self, hub: Hub) -> Any:
        if hub.color:
            return self.get_color_from_string(hub.color)
        if hub.is_start:
            return arcade.color.GREEN
        if hub.is_end:
            return arcade.color.RED

        zone = str(hub.zone_type).lower()
        if "high" in zone:
            return arcade.color.ORANGE
        if "medium" in zone:
            return arcade.color.BLUE
        if "low" in zone:
            return arcade.color.SKY_BLUE

        return arcade.color.GRAY

    def build_hub_sprites(self) -> None:
        self.hub_sprites = arcade.SpriteList()
        self.hub_markers = arcade.SpriteList()
        self.hub_name_texts = []

        marker_texture = arcade.make_circle_texture(30, arcade.color.WHITE)

        for name, hub in self.hubs.items():
            x, y = self.hub_screen_positions[name]
            base_size = self.get_hub_display_size()
            s = base_size / 35.0
            island_sprite = arcade.Sprite(
                self.island,
                center_x=x,
                center_y=y,
                scale=self.get_hub_scale()
            )
            self.hub_sprites.append(island_sprite)
            marker_sprite = arcade.Sprite(
                marker_texture,
                scale=(10 * s) / marker_texture.width
            )
            offset_val = 12 * s
            marker_sprite.center_x = x + offset_val
            marker_sprite.center_y = y + offset_val
            marker_sprite.color = self.get_hub_color(hub)
            marker_sprite.alpha = 200
            self.hub_markers.append(marker_sprite)
            name_text = arcade.Text(
                name.replace("_", " ").title(),
                x,
                y - (22 * s),
                arcade.color.WHITE,
                min(20, max(10, int(12 * s))),
                anchor_x="center",
                anchor_y="center",
                align="center",
                multiline=True,
                width=8
            )
            self.hub_name_texts.append(name_text)

    def compute_scale(self) -> None:
        if not self.hubs:
            return

        xs = [int(hub.x) for hub in self.hubs.values()]
        ys = [int(hub.y) for hub in self.hubs.values()]

        self.min_x, self.max_x = min(xs), max(xs)
        self.min_y, self.max_y = min(ys), max(ys)

        map_w = max(self.max_x - self.min_x, 1)
        map_h = max(self.max_y - self.min_y, 1)

        usable_w = self.window.width - 2 * self.margin
        usable_h = self.window.height - 2 * self.margin

        scale_x = usable_w / map_w
        scale_y = usable_h / map_h
        self.scale = min(scale_x, scale_y)

        actual_map_w = map_w * self.scale
        actual_map_h = map_h * self.scale

        self.offset_x = (self.window.width - actual_map_w) / 2
        self.offset_y = (self.window.height - actual_map_h) / 2

    def get_hub_capacity_labels(self, turn: int) -> Dict[str, str]:
        occupancy = {name: 0 for name in self.hubs}

        for drone in self.drones:
            state = self.get_drone_state_at_turn(drone, turn)
            if "->" not in state:
                occupancy[state] += 1

        labels = {}
        for name, hub in self.hubs.items():
            current = occupancy[name]
            if current == 0:
                continue
            if hub.is_start or hub.is_end:
                labels[name] = f"{current}/∞"
            else:
                labels[name] = f"{current}/{hub.max_drones}"
        return labels

    def update_hub_capacity_texts(self) -> None:
        self.text_objects["hub_capacity"] = []
        self.text_objects["hub_zone"] = []

        labels = self.get_hub_capacity_labels(self.current_turn)
        base_size = self.get_hub_display_size()
        s = base_size / 35.0

        for name, hub in self.hubs.items():
            x, y = self.hub_screen_positions[name]

            if name in labels:
                capacity_label = arcade.Text(
                    labels[name],
                    x - (18 * s),
                    y + (18 * s),
                    arcade.color.WHITE,
                    font_size=min(16, max(10, int(10 * s))),
                    anchor_x="right",
                    anchor_y="bottom",
                    bold=True,
                )
                self.text_objects["hub_capacity"].append(capacity_label)

            zone_text = str(hub.zone_type).split(".")[-1].upper()
            zone_label = arcade.Text(
                zone_text,
                x + (18 * s),
                y + (18 * s),
                arcade.color.LIGHT_GRAY,
                font_size=min(14, max(8, int(9 * s))),
                anchor_x="left",
                anchor_y="bottom",
            )
            self.text_objects["hub_zone"].append(zone_label)

    def transform_position(self,
                           x: float | int,
                           y: float | int) -> Tuple[float, float]:
        screen_x = self.offset_x + (int(x) - self.min_x) * self.scale
        screen_y = self.offset_y + (int(y) - self.min_y) * self.scale
        return float(screen_x), float(screen_y)

    def go_back(self, event: arcade.gui.UIOnClickEvent) -> None:
        from welcomepage import WelcomeView
        self.window.show_view(WelcomeView())

    def on_draw(self) -> None:
        self.clear()
        arcade.draw_texture_rect(
            self.background,
            arcade.rect.XYWH(
                self.window.width / 2,
                self.window.height / 2,
                self.window.width,
                self.window.height,
            ),
        )
        self.draw_connections()
        self.draw_hubs()
        for text in self.hub_name_texts:
            text.draw()
        self.drone_sprites.draw()
        self.draw_header()
        self.ui.draw()

    def draw_header(self) -> None:
        for key in ("map", "drones", "stats"):
            self.text_objects[key].draw()
        for label in self.text_objects["hub_capacity"]:
            label.draw()
        for label in self.text_objects["hub_zone"]:
            label.draw()

    def get_hub_display_size(self) -> float:
        hub_count = len(self.hubs)
        if hub_count == 0:
            return 28.0
        base_size = 200 / (hub_count ** 0.5)
        return float(min(max(base_size, 28), 80))

    def get_connection_offset(self) -> float:
        return self.get_hub_display_size() * 0.45

    def get_connection_endpoints(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        offset: float
    ) -> Tuple[float, float, float, float]:
        dx = x2 - x1
        dy = y2 - y1
        distance = math.hypot(dx, dy)
        if distance == 0:
            return x1, y1, x2, y2
        ux = dx / distance
        uy = dy / distance
        return (x1 + ux * offset,
                y1 + uy * offset,
                x2 - ux * offset,
                y2 - uy * offset)

    def draw_connections(self) -> None:
        offset = self.get_connection_offset()
        for conn in self.connections:
            x1, y1 = self.hub_screen_positions[conn.source.name]
            x2, y2 = self.hub_screen_positions[conn.target.name]
            sx, sy, ex, ey = self.get_connection_endpoints(
                x1, y1, x2, y2, offset)

            arcade.draw_line(sx, sy, ex, ey, arcade.color.DARK_SLATE_GRAY, 6)
            arcade.draw_line(sx, sy, ex, ey, arcade.color.LIGHT_GRAY, 3)

            if conn.target.cost == 2:
                mid_x, mid_y = (sx + ex) / 2, (sy + ey) / 2
                s = self.get_hub_display_size() / 35.0
                arcade.draw_ellipse_filled(
                    mid_x + (2 * s),
                    mid_y - (2 * s),
                    14 * s,
                    10 * s,
                    (0, 0, 0, 100))
                arcade.draw_ellipse_filled(
                    mid_x, mid_y, 14 * s, 10 * s, arcade.color.DARK_BROWN)
                arcade.draw_ellipse_filled(
                    mid_x, mid_y, 12 * s, 8.5 * s, arcade.color.GOLDEN_BROWN)
                arcade.draw_ellipse_filled(
                    mid_x, mid_y, 10 * s, 7 * s, arcade.color.GOLD)

    def draw_hubs(self) -> None:
        self.hub_sprites.draw()
        self.hub_markers.draw()

    def get_finished_turn(self) -> int:
        if not self.drones:
            return 0
        max_t = 0
        for drone in self.drones:
            if drone.route:
                max_t = max(max_t, len(drone.route) - 1)
        return max_t

    def on_next_turn(self, event: arcade.gui.UIOnClickEvent) -> None:
        if self.turn_animating or self.current_turn >= self.max_turn:
            return
        self.target_turn = self.current_turn + 1
        self.turn_progress = 0.0
        self.turn_animating = True

    def on_update(self, delta_time: float) -> None:
        if not self.turn_animating:
            return
        self.turn_progress += delta_time / self.turn_animation_duration
        if self.turn_progress >= 1.0:
            self.turn_progress = 1.0
            self.update_drone_positions_for_animation()
            self.current_turn = self.target_turn
            self.turn_animating = False
            self.turn_progress = 0.0
            self.update_drone_positions_static()
            self.refresh_turn_label()
            self.update_hub_capacity_texts()
            return
        self.update_drone_positions_for_animation()

    def update_drone_positions_static(self) -> None:
        for drone in self.drones:
            sprite = self.drone_sprite_map[drone.drone_id]
            state = self.get_drone_state_at_turn(drone, self.current_turn)
            x, y = self.get_state_position(state)
            sprite.center_x, sprite.center_y = x, y

    def update_drone_positions_for_animation(self) -> None:
        for drone in self.drones:
            sprite = self.drone_sprite_map[drone.drone_id]
            start_state = self.get_drone_state_at_turn(
                drone, self.current_turn)
            end_state = self.get_drone_state_at_turn(
                drone, self.target_turn)
            x, y = self.get_interpolated_position(
                start_state, end_state, self.turn_progress)
            sprite.center_x, sprite.center_y = x, y

    def get_drone_state_at_turn(self, drone: Drone, turn: int) -> str:
        if not drone.route:
            return str(self.start_hub.name)
        return (
            drone.route[turn] if turn < len(drone.route) else drone.route[-1])

    def get_interpolated_position(
        self, start_state: str, end_state: str, progress: float
    ) -> Tuple[float, float]:
        x1, y1 = self.get_state_position(start_state)
        x2, y2 = self.get_state_position(end_state)
        return x1 + (x2 - x1) * progress, y1 + (y2 - y1) * progress

    def refresh_turn_label(self) -> None:
        if self.turn_label:
            self.turn_label.text = f"TURN {self.current_turn}"

    def build_drone_sprites(self) -> None:
        self.drone_sprites = arcade.SpriteList()
        self.drone_sprite_map = {}
        drone_texture = arcade.make_circle_texture(20, arcade.color.WHITE)
        for drone in self.drones:
            sprite = arcade.Sprite(drone_texture, scale=0.6)
            sprite.color = arcade.color.SKY_BLUE
            self.drone_sprites.append(sprite)
            self.drone_sprite_map[drone.drone_id] = sprite

    def get_state_position(self, state: str) -> Tuple[float, float]:
        if "->" in state:
            src, tgt = state.split("->", 1)
            x1, y1 = self.hub_screen_positions[src]
            x2, y2 = self.hub_screen_positions[tgt]
            return (x1 + x2) / 2, (y1 + y2) / 2
        return self.hub_screen_positions[state]
