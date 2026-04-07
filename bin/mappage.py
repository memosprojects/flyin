import arcade
import arcade.gui
from pathlib import Path
import math

from parser import MapParser
from algorithm import DronePlanner


class MapView(arcade.View):
    def __init__(self, map_path: str, map_name: str):
        super().__init__()

        self.map_path = Path(map_path)
        self.map_name = map_name

        self.ui = arcade.gui.UIManager()
        self.background = arcade.load_texture(
            Path(__file__).parent
            / ".."
            / "uilibrary"
            / "background.jpeg"
        )
        self.anchor = arcade.gui.UIAnchorLayout()

        self.parsed_data = None
        self.hubs = {}
        self.connections = []
        self.drone_count = 0

        self.margin = 80
        self.scale = 1.0

        self.text_objects = {}

        self.load_textures()

        # Animation assets
        self.current_turn = 0
        self.target_turn = 0

        self.turn_animating = False
        self.turn_progress = 0.0
        self.turn_animation_duration = 0.6

        self.drones = []
        self.drone_sprites = arcade.SpriteList()
        self.drone_sprite_map = {}
        self.turn_label = None

        self.max_turn = self.get_finished_turn()

    def load_textures(self):
        islandsheet = arcade.load_spritesheet(
            Path(__file__).parent
            / ".."
            / "uilibrary"
            / "Island.png"
        )

        self.island = islandsheet.get_texture(
            rect=arcade.LBWH(0, 1, 47, 71)
        )

    def get_hub_scale(self):
        return self.get_hub_display_size() / self.island.width

    def on_show_view(self):
        self.ui.enable()
        self.ui.add(self.anchor)

        back_button = arcade.gui.UIFlatButton(
            text="Back",
            width=120,
        )
        back_button.on_click = self.go_back

        next_button = arcade.gui.UIFlatButton(
            text="Next Turn",
            width=140,
        )
        next_button.on_click = self.on_next_turn

        quit_button = arcade.gui.UIFlatButton(
            text="Quit",
            width=120,
        )
        quit_button.on_click = self.quit_game

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

    def quit_game(self, event):
        arcade.exit()

    def on_hide_view(self):
        self.ui.disable()

    def load_map(self):
        parser = MapParser(self.map_path)
        self.parsed_data = parser.parse()

        self.drone_count = self.parsed_data["drone_count"]
        self.hubs = self.parsed_data["hubs"]
        self.connections = self.parsed_data["connections"]

        planner = DronePlanner(self.parsed_data)
        self.drones = planner.plan_all_drones(max_turns=200)
        self.max_turn = self.get_finished_turn()

        self.start_hub = next(hub for hub in self.hubs.values() if hub.is_start)

        self.compute_scale()

        self.hub_screen_positions = {}
        for name, hub in self.hubs.items():
            self.hub_screen_positions[name] = self.transform_position(hub.x, hub.y)
        self.build_hub_sprites()
        self.build_drone_sprites()
        self.refresh_turn_label()
        self.update_drone_positions_static()

    def setup_texts(self):
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
            f"Hubs: {len(self.hubs)} | Connections: {len(self.connections)}",
            160,
            self.window.height - 90,
            arcade.color.LIGHT_GRAY,
            14,
        )

    def get_color_from_string(self, color_str: str):
        if not color_str:
            return None

        color_str = color_str.upper().strip()
        if color_str.startswith("#"):
            try:
                return arcade.color_from_hexstring(color_str)
            except ValueError:
                return arcade.color.GRAY
        try:
            return getattr(arcade.color, color_str)
        except AttributeError:
            return arcade.color.GRAY

    def get_hub_color(self, hub):
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

    def build_hub_sprites(self):
        self.hub_sprites = arcade.SpriteList()
        self.hub_markers = arcade.SpriteList() 
        self.hub_name_texts = []

        # Marker dokusunu oluştur (beyaz, üzerine renk binecek)
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

    def compute_scale(self):
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

    def transform_position(self, x, y):
        screen_x = self.offset_x + (int(x) - self.min_x) * self.scale
        screen_y = self.offset_y + (int(y) - self.min_y) * self.scale
        return screen_x, screen_y

    def go_back(self, event):
        from welcomepage import WelcomeView
        self.window.show_view(WelcomeView())

    def on_draw(self):
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

    def draw_header(self):
        for text in self.text_objects.values():
            text.draw()

    def get_hub_display_size(self):
        hub_count = len(self.hubs)
        if hub_count == 0:
            return 28

        base_size = 200 / (hub_count ** 0.5)
        return min(max(base_size, 28), 80)

    def get_connection_offset(self):
        return self.get_hub_display_size() * 0.45

    def get_connection_endpoints(self, x1, y1, x2, y2, offset):
        dx = x2 - x1
        dy = y2 - y1
        distance = math.hypot(dx, dy)

        if distance == 0:
            return x1, y1, x2, y2

        ux = dx / distance
        uy = dy / distance

        start_x = x1 + ux * offset
        start_y = y1 + uy * offset
        end_x = x2 - ux * offset
        end_y = y2 - uy * offset

        return start_x, start_y, end_x, end_y

    def draw_connections(self):
        offset = self.get_connection_offset()

        for conn in self.connections:
            x1, y1 = self.hub_screen_positions[conn.source.name]
            x2, y2 = self.hub_screen_positions[conn.target.name]

            sx, sy, ex, ey = self.get_connection_endpoints(x1, y1, x2, y2, offset)

            arcade.draw_line(sx, sy, ex, ey, arcade.color.DARK_SLATE_GRAY, 6)
            arcade.draw_line(sx, sy, ex, ey, arcade.color.LIGHT_GRAY, 3)

            if conn.target.cost == 2:
                mid_x = (sx + ex) / 2
                mid_y = (sy + ey) / 2

                base_size = self.get_hub_display_size()
                s = base_size / 35.0

                arcade.draw_ellipse_filled(mid_x + (2 * s), mid_y - (2 * s), 14 * s, 10 * s, (0, 0, 0, 100))

                arcade.draw_ellipse_filled(mid_x, mid_y, 14 * s, 10 * s, arcade.color.DARK_BROWN)

                arcade.draw_ellipse_filled(mid_x, mid_y, 12 * s, 8.5 * s, arcade.color.GOLDEN_BROWN)

                arcade.draw_ellipse_filled(mid_x, mid_y, 10 * s, 7 * s, arcade.color.GOLD)

    def draw_hubs(self):
        self.hub_sprites.draw()
        self.hub_markers.draw()

    def get_finished_turn(self) -> int:
        if not self.drones:
            return 0

        max_turn = 0
        for drone in self.drones:
            if drone.route:
                max_turn = max(max_turn, len(drone.route) - 1)

        return max_turn

    def on_next_turn(self, event):
        if self.turn_animating:
            return

        if self.current_turn >= self.max_turn:
            return

        self.target_turn = self.current_turn + 1
        self.turn_progress = 0.0
        self.turn_animating = True

    def on_update(self, delta_time: float):
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
            return

        self.update_drone_positions_for_animation()

    def update_drone_positions_static(self):
        for drone in self.drones:
            sprite = self.drone_sprite_map[drone.drone_id]

            state = self.get_drone_state_at_turn(drone, self.current_turn)
            x, y = self.get_state_position(state)

            sprite.center_x = x
            sprite.center_y = y

    def update_drone_positions_for_animation(self):
        for drone in self.drones:
            sprite = self.drone_sprite_map[drone.drone_id]

            start_state = self.get_drone_state_at_turn(drone, self.current_turn)
            end_state = self.get_drone_state_at_turn(drone, self.target_turn)

            x, y = self.get_interpolated_position(
                start_state,
                end_state,
                self.turn_progress,
            )

            sprite.center_x = x
            sprite.center_y = y

    def get_drone_state_at_turn(self, drone, turn: int) -> str:
        if not drone.route:
            return self.start_hub.name

        if turn < len(drone.route):
            return drone.route[turn]

        return drone.route[-1]

    def get_interpolated_position(
        self,
        start_state: str,
        end_state: str,
        progress: float,
    ) -> tuple[float, float]:
        x1, y1 = self.get_state_position(start_state)
        x2, y2 = self.get_state_position(end_state)

        x = x1 + (x2 - x1) * progress
        y = y1 + (y2 - y1) * progress
        return x, y

    def refresh_turn_label(self):
        if self.turn_label:
            self.turn_label.text = f"TURN {self.current_turn}"

    def build_drone_sprites(self):
        self.drone_sprites = arcade.SpriteList()
        self.drone_sprite_map = {}

        drone_texture = arcade.make_circle_texture(20, arcade.color.WHITE)

        for drone in self.drones:
            sprite = arcade.Sprite(drone_texture, scale=0.6)
            sprite.color = arcade.color.SKY_BLUE
            self.drone_sprites.append(sprite)
            self.drone_sprite_map[drone.drone_id] = sprite

    def get_state_position(self, state: str) -> tuple[float, float]:
        if "->" in state:
            source_name, target_name = state.split("->", 1)
            x1, y1 = self.hub_screen_positions[source_name]
            x2, y2 = self.hub_screen_positions[target_name]
            return (x1 + x2) / 2, (y1 + y2) / 2

        return self.hub_screen_positions[state]
