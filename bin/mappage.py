import arcade
import arcade.gui
from pathlib import Path

from parser import MapParser


class MapView(arcade.View):
    def __init__(self, map_path: str):
        super().__init__()

        self.map_path = Path(map_path)

        self.ui = arcade.gui.UIManager()
        self.anchor = arcade.gui.UIAnchorLayout()

        self.parsed_data = None
        self.hubs = {}
        self.connections = []
        self.drone_count = 0

        self.margin = 80
        self.scale = 1.0

        uibattlepath = Path("../uilibrary/kenney_tiny-battle/Tilemap/tilemap_packed.png")
        battlesheet = arcade.load_spritesheet(uibattlepath)
        battletextures = battlesheet.get_texture_grid(
            size=(16, 16),
            columns=18,
            count=198,
        )

    def on_show_view(self):
        self.ui.enable()
        self.ui.add(self.anchor)

        back_button = arcade.gui.UIFlatButton(
            text="Back",
            width=120,
        )
        back_button.on_click = self.go_back

        self.anchor.add(
            child=back_button,
            anchor_x="left",
            anchor_y="top",
            align_x=20,
            align_y=-20,
        )

        self.load_map()

    def on_hide_view(self):
        self.ui.disable()

    def load_map(self):
        parser = MapParser(self.map_path)
        self.parsed_data = parser.parse()

        self.drone_count = self.parsed_data["drone_count"]
        self.hubs = self.parsed_data["hubs"]
        self.connections = self.parsed_data["connections"]

        self.compute_scale()

        self.hub_screen_positions = {}
        for name, hub in self.hubs.items():
            self.hub_screen_positions[name] = self.transform_position(hub.x, hub.y)

    def compute_scale(self):
        if not self.hubs:
            return

        xs = [int(hub.x) for hub in self.hubs.values()]
        ys = [int(hub.y) for hub in self.hubs.values()]

        self.min_x = min(xs)
        self.max_x = max(xs)
        self.min_y = min(ys)
        self.max_y = max(ys)

        map_w = max(self.max_x - self.min_x, 1)
        map_h = max(self.max_y - self.min_y, 1)

        usable_w = self.window.width - 2 * self.margin
        usable_h = self.window.height - 2 * self.margin

        scale_x = usable_w / map_w
        scale_y = usable_h / map_h
        self.scale = min(scale_x, scale_y)

    def transform_position(self, x, y):
        x = int(x)
        y = int(y)

        screen_x = self.margin + (x - self.min_x) * self.scale
        screen_y = self.margin + (y - self.min_y) * self.scale

        return screen_x, screen_y

    def go_back(self, event):
        from WelcomePage import WelcomeView
        self.window.show_view(WelcomeView())

    def on_draw(self):
        self.clear(color=arcade.color.BLACK)

        self.draw_header()
        self.draw_connections()
        self.draw_hubs()

    def draw_header(self):
        arcade.draw_text(
            f"MAP: {self.map_path.name}",
            160,
            self.window.height - 35,
            arcade.color.WHITE,
            18,
            bold=True,
        )

        arcade.draw_text(
            f"Drones: {self.drone_count}",
            160,
            self.window.height - 65,
            arcade.color.LIGHT_GRAY,
            14,
        )

        arcade.draw_text(
            f"Hubs: {len(self.hubs)} | Connections: {len(self.connections)}",
            160,
            self.window.height - 90,
            arcade.color.LIGHT_GRAY,
            14,
        )

    def draw_connections(self):
        for conn in self.connections:
            x1, y1 = self.hub_screen_positions[conn.source.name]
            x2, y2 = self.hub_screen_positions[conn.target.name]

            arcade.draw_line(x1, y1, x2, y2, arcade.color.LIGHT_GRAY, 3)

    def draw_hubs(self):
        for name, hub in self.hubs.items():
            x, y = self.hub_screen_positions[name]

            color = self.get_hub_color(hub)
            radius = self.get_hub_radius(hub)

            arcade.draw_circle_filled(x, y, radius, color)
            arcade.draw_circle_outline(x, y, radius, arcade.color.WHITE, 2)

    def get_hub_color(self, hub):
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

    def get_hub_radius(self, hub):
        base = 18
        bonus = min(int(hub.max_drones), 5) * 2
        return base + bonus