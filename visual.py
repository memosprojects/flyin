import arcade
from Units import Hub, Connection
from parser import MapParser
from pathlib import Path


class VisualInterface(arcade.Window):

    COLOR_MAP = {
        "red": arcade.color.RED,
        "blue": arcade.color.BLUE,
        "green": arcade.color.GREEN,
        "yellow": arcade.color.YELLOW,
        "gray": arcade.color.GRAY,
        "none": arcade.color.WHITE
    }

    def __init__(self,
                 hubs: dict[str, Hub],
                 connections: list[Connection],
                 width=1200, height=800
                 ):
        super().__init__(width, height, "Fly-in Simulation")
        arcade.set_background_color(arcade.color.BLACK_OLIVE)

        self.hubs = hubs
        self.connections = connections
        self.margin = 80

        # 1. Calculate Bounds
        coords_x = [h.x for h in hubs.values()]
        coords_y = [h.y for h in hubs.values()]
        
        self.min_x, self.max_x = min(coords_x), max(coords_x)
        self.min_y, self.max_y = min(coords_y), max(coords_y)

        range_x = (self.max_x - self.min_x) if self.max_x != self.min_x else 1
        range_y = (self.max_y - self.min_y) if self.max_y != self.min_y else 1

        self.scale_x = (width - 2 * self.margin) / range_x
        self.scale_y = (height - 2 * self.margin) / range_y

    def map_to_pixel(self, x: int, y: int):
        """Converts map units to screen pixels using dynamic scaling."""
        px = self.margin + (x - self.min_x) * self.scale_x
        py = self.margin + (y - self.min_y) * self.scale_y
        return px, py
    
    def on_draw(self):
        self.clear()
        
        # Draw Connections
        for conn in self.connections:
            x1, y1 = self.map_to_pixel(conn.source.x, conn.source.y)
            x2, y2 = self.map_to_pixel(conn.target.x, conn.target.y)
            arcade.draw_line(x1, y1, x2, y2, arcade.color.RED, 2)
            
        # Draw Hubs
        for hub in self.hubs.values():
            px, py = self.map_to_pixel(hub.x, hub.y)
            
            # Draw Hub Circle
            color = arcade.color.GREEN if hub.is_start else arcade.color.RED if hub.is_end else arcade.color.LIGHT_BLUE
            arcade.draw_circle_filled(px, py, 12, color)
            
            # Label
            arcade.draw_text(hub.name, px, py + 15, arcade.color.WHITE, 10, anchor_x="center")


def main():

    map_path = Path("maps/hard/03_ultimate_challenge.txt") 
    
    if not map_path.exists():
        print(f"Error: {map_path} not found.")
        return

    # 2. Parse İşlemi
    parser = MapParser(map_path)
    try:
        data = parser.parse()
        # Bağlantıları kur (Neighbors listesini doldurur)
        parser._make_connections()
        
        print(f"Map parsed successfully: {len(data['hubs'])} hubs found.")
        
        # 3. Görselleştirmeyi Başlat
        # Hub'lar ve Connection'lar parser'dan geliyor
        visualizer = VisualInterface(data['hubs'], data['connections'])
        arcade.run()
        
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
