import arcade
import arcade.gui
from pathlib import Path
from arcade.gui import NinePatchTexture, UIView
from MapManager import MapFolderManager
from mappage import MapView


SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 800
SCREEN_TITLE = "Flyin - Welcome"


class UIAssets:
    def __init__(self):
        path_to_ui = ("/home/mehdemir/Projects/Fly/uilibrary/kenney_ui-pack-pixel-adventure/Tilesheets/Large tiles/Thick outline/tilemap_packed.png"
        )
        sheet = arcade.load_spritesheet(path_to_ui)
        self.textures = sheet.get_texture_grid(
            size=(16, 16),
            columns=13,
            count=91,
        )

        uibattlepath = Path("../uilibrary/kenney_tiny-battle/Tilemap/tilemap_packed.png")
        battlesheet = arcade.load_spritesheet(uibattlepath)
        self.battletextures = battlesheet.get_texture_grid(
            size=(16, 16),
            columns=18,
            count=198,
        )

    def get_window(self, col: int, row: int, border: int = 12) -> NinePatchTexture:
        texture = self.textures[row * 13 + col]
        return NinePatchTexture(
            left=border,
            right=border,
            bottom=border,
            top=border,
            texture=texture,
        )

    def get_texture(self, col: int, row: int):
        return self.textures[row * 13 + col]
    
    def get_battletexture(self, col: int, row: int):
        return self.textures[row * 13 + col]


class WelcomeView(UIView):
    def __init__(self):
        super().__init__()

        self.ui_assets = UIAssets()

        self.bg_panel = self.ui_assets.get_window(0, 6)
        self.header_panel = self.ui_assets.get_window(2, 0)
        self.button_tex = self.ui_assets.get_window(9, 1)
        self.button_hover = self.ui_assets.get_window(9, 1)
        self.button_pressed = self.ui_assets.get_window(9, 2)

        self.selected_map_path = None

        self.anchor = arcade.gui.UIAnchorLayout()
        self.add_widget(self.anchor)

        self.v_box = arcade.gui.UIBoxLayout(space_between=10)

        title_label = arcade.gui.UILabel(
            text="WELCOME, PLEASE CHOOSE THE MAP",
            font_size=20,
            text_color=arcade.color.WHITE,
            bold=True,
        )
        self.v_box.add(title_label.with_padding(bottom=30, top=12))

        map_dir = MapFolderManager().map_list

        category_order = {
            "easy": 0,
            "medium": 1,
            "hard": 2,
            "challenger": 3,
        }

        if not map_dir:
            empty_label = arcade.gui.UILabel(
                text="No maps found.",
                font_size=16,
                text_color=arcade.color.RED,
            )
            self.v_box.add(empty_label)
        else:
            for _, map_info in sorted(
                map_dir.items(),
                key=lambda item: (
                    category_order.get(item[1]["category"], 99),
                    item[1]["number"],
                    item[1]["name"],
                ),
            ):
                map_name = map_info["name"]
                map_path = map_info["address"]
                normal_tex, hover_tex, pressed_tex = self.get_button_textures_by_category(map_info["category"])

                button = arcade.gui.UITextureButton(
                    texture=normal_tex,
                    texture_hovered=hover_tex,
                    texture_pressed=pressed_tex,
                    text=map_name,
                    width=240,
                    height=36,
                )

                button.on_click = self.make_map_handler(map_name, map_path)
                self.v_box.add(button)

        self.anchor.add(
            child=self.v_box,
            anchor_x="center_x",
            anchor_y="center_y",
            align_y=0
        )

    def make_map_handler(self, map_name, map_path):
        def on_click(event):
            self.selected_map_path = map_path
            print(f"Selected map: {map_name}")
            print(f"Map path: {map_path}")

            # parser burada veya MapView içinde çalışabilir
            map_view = MapView(map_path=map_path)
            self.window.show_view(map_view)

        return on_click

    def get_button_textures_by_category(self, category: str):
        if category == "easy":
            return (
                self.ui_assets.get_window(5, 0, border=6),
                self.ui_assets.get_window(9, 1, border=6),
                self.ui_assets.get_window(9, 2, border=6),
            )
        if category == "medium":
            return (
                self.ui_assets.get_window(5, 0, border=6),
                self.ui_assets.get_window(8, 1, border=6),
                self.ui_assets.get_window(7, 2, border=6),
            )
        if category == "hard":
            return (
                self.ui_assets.get_window(5, 0, border=6),
                self.ui_assets.get_window(7, 1, border=6),
                self.ui_assets.get_window(5, 2, border=6),
            )
        return (
            self.ui_assets.get_window(5, 0, border=6),
            self.ui_assets.get_window(7, 2, border=6),
            self.ui_assets.get_window(9, 2, border=6),
        )

    def on_draw_before_ui(self):
        self.clear()

        center_x = self.window.width / 2
        center_y = self.window.height / 2

        main_rect = arcade.XYWH(center_x, center_y, 800, 600)
        self.bg_panel.draw_rect(rect=main_rect)

        header_rect = arcade.XYWH(center_x, center_y + 240, 600, 80)
        self.header_panel.draw_rect(rect=header_rect)


def main():
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    welcome_view = WelcomeView()
    window.show_view(welcome_view)
    arcade.run()


if __name__ == "__main__":
    main()
