import arcade
import arcade.gui
from pathlib import Path
import math

from parser import MapParser


class MapView(arcade.View):
    def __init__(self, map_path: str, map_name: str):
        super().__init__()

        self.map_path = Path(map_path)
        self.map_name = map_name

        self.ui = arcade.gui.UIManager()
        self.background = arcade.load_texture("/home/mehdemir/Projects/Fly/uilibrary/background.jpeg")
        self.anchor = arcade.gui.UIAnchorLayout()

        self.parsed_data = None
        self.hubs = {}
        self.connections = []
        self.drone_count = 0

        self.margin = 80
        self.scale = 1.0

        self.text_objects = {}

        self.load_textures()

    def load_textures(self):
        islandsheet = arcade.load_spritesheet("/home/mehdemir/Projects/Fly/uilibrary/Island.png")
        self.island = islandsheet.get_texture(
            rect=arcade.LBWH(0, 1, 47, 71)
        )

    def get_hub_scale(self, hub):
        hub_count = len(self.hubs)

        # ters orantı: az hub = büyük, çok hub = küçük
        base_size = 200 / (hub_count ** 0.5)

        # sınırlar (çok önemli)
        base_size = min(max(base_size, 28), 80)

        return base_size / self.island.width

    def get_hub_texture(self, hub):
        if hub.is_start:
            return self.island  # şimdilik test texture
        if hub.is_end:
            return self.island

        return self.island

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
        self.setup_texts()

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
        self.build_hub_sprites()

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
        
        # 1. Check if it's a hex code (e.g., #FF5733)
        if color_str.startswith("#"):
            try:
                return arcade.color_from_hexstring(color_str)
            except ValueError:
                return arcade.color.GRAY # Fallback for invalid hex

        # 2. Check if it's a standard Arcade color constant
        # We use getattr to find the color in the arcade.color module
        try:
            return getattr(arcade.color, color_str)
        except AttributeError:
            # 3. Fallback: If color name is unknown
            return arcade.color.GRAY
        
    def get_hub_color(self, hub):
        # 1. Priority: Explicit color from the Hub data
        if hub.color:
            return self.get_color_from_string(hub.color)

        # 2. Secondary: Start/End status
        if hub.is_start:
            return arcade.color.GREEN
        if hub.is_end:
            return arcade.color.RED

        # 3. Tertiary: Zone-based coloring
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

                # 1. Hub Ölçek Çarpanı (Senin formülünle)
                base_size = self.get_hub_display_size()
                s = base_size / 35.0

                # 2. Ada Sprite'ı
                island_sprite = arcade.Sprite(
                    self.get_hub_texture(hub),
                    center_x=x,
                    center_y=y,
                    scale=self.get_hub_scale(hub)
                )
                self.hub_sprites.append(island_sprite)

                # 3. Marker (Renk Topu) Sprite'ı
                # Boyutu 's' çarpanına göre belirle (Örn: baz boyut 10px * s)
                marker_sprite = arcade.Sprite(
                    marker_texture,
                    scale=(10 * s) / marker_texture.width 
                )

                # Pozisyonu perspektife göre kaydır (Sağ üst çapraz)
                # Kayma miktarını da 's' ile çarpıyoruz ki küçük hublarda top adanın dışına taşmasın
                offset_val = 12 * s
                marker_sprite.center_x = x + offset_val
                marker_sprite.center_y = y + offset_val

                # Renk ve Stil
                marker_sprite.color = self.get_hub_color(hub)
                marker_sprite.alpha = 200 # Hafif şeffaflık derinlik katar

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

        # --- Ortalamak için Offset Hesaplama ---
        # Haritanın ekrandaki gerçek boyutu
        actual_map_w = map_w * self.scale
        actual_map_h = map_h * self.scale

        # X ve Y eksenindeki boşlukları paylaştır
        self.offset_x = (self.window.width - actual_map_w) / 2
        self.offset_y = (self.window.height - actual_map_h) / 2

    def transform_position(self, x, y):
        # Margin yerine doğrudan hesaplanan offset'i kullanıyoruz
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
        self.draw_header()
        self.draw_connections()
        self.draw_hubs()
        for text in self.hub_name_texts:
            text.draw()
        self.ui.draw()

    def draw_header(self):
        for text in self.text_objects.values():
            text.draw()

    def get_hub_display_size(self):
        hub_count = len(self.hubs)
        base_size = 200 / (hub_count ** 0.5)
        return min(max(base_size, 28), 80)

    def get_hub_scale(self, hub):
        return self.get_hub_display_size() / self.island.width

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
                
                # Hub boyutuna göre dinamik ölçek hesabı (Örn: hub 40px ise scale_factor 1.0 civarı olur)
                # 35.0 burada "ideal" oran için seçilmiş bir baz değerdir.
                base_size = self.get_hub_display_size()
                s = base_size / 35.0 

                # 1. Gölge (Shadow) - Hafif kaydırılmış
                arcade.draw_ellipse_filled(mid_x + (2 * s), mid_y - (2 * s), 14 * s, 10 * s, (0, 0, 0, 100))

                # 2. Dış Çerçeve
                arcade.draw_ellipse_filled(mid_x, mid_y, 14 * s, 10 * s, arcade.color.DARK_BROWN)

                # 3. Ana Gövde
                arcade.draw_ellipse_filled(mid_x, mid_y, 12 * s, 8.5 * s, arcade.color.GOLDEN_BROWN)

                # 4. Parlama (Highlight)
                arcade.draw_ellipse_filled(mid_x, mid_y, 10 * s, 7 * s, arcade.color.GOLD)

    def draw_hubs(self):
        self.hub_sprites.draw()
        self.hub_markers.draw()



