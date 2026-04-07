import arcade
import arcade.gui
from pathlib import Path
from typing import Callable, Any, Tuple
from arcade.gui import NinePatchTexture, UIView
from MapManager import MapFolderManager
from mappage import MapView


class UIAssets:
    def __init__(self) -> None:
        path_to_ui: Path = (
            Path(__file__).parent
            / ".."
            / "uilibrary"
            / "kenney_ui-pack-pixel-adventure"
            / "Tilesheets"
            / "Large tiles"
            / "Thick outline"
            / "tilemap_packed.png"
        ).resolve()
        sheet: arcade.SpriteSheet = arcade.load_spritesheet(path_to_ui)
        self.textures: list[arcade.Texture] = sheet.get_texture_grid(
            size=(32, 32),
            columns=13,
            count=91,
        )

        mapui: Path = (
            Path(__file__).parent
            / ".."
            / "uilibrary"
            / "dungeon_tiles.png"
        ).resolve()
        mapuisheet: arcade.SpriteSheet = arcade.load_spritesheet(mapui)
        self.mapui: list[arcade.Texture] = mapuisheet.get_texture_grid(
            size=(16, 16),
            columns=18,
            count=198,
        )

    def get_window(self,
                   col: int,
                   row: int,
                   border: int = 5
                   ) -> NinePatchTexture:
        texture: arcade.Texture = self.textures[row * 13 + col]
        return NinePatchTexture(
            left=border,
            right=border,
            bottom=border,
            top=border,
            texture=texture,
        )

    def get_texture(self, col: int, row: int) -> arcade.Texture:
        return self.textures[row * 13 + col]

    def get_battletexture(self, col: int, row: int) -> arcade.Texture:
        return self.textures[row * 13 + col]


class WelcomeView(UIView):
    def __init__(self) -> None:
        super().__init__()
        KENNEY_FONT_PATH: str = ':resources:/fonts/ttf/Kenney/Kenney_Pixel.ttf'
        KENNEY_FONT_NAME: str = "Kenney Pixel"
        arcade.load_font(KENNEY_FONT_PATH)
        self.ui_assets: UIAssets = UIAssets()

        self.bg_panel: NinePatchTexture = self.ui_assets.get_window(0, 0)
        self.header_panel: NinePatchTexture = self.ui_assets.get_window(2, 0)
        self.button_tex: NinePatchTexture = self.ui_assets.get_window(9, 1)
        self.button_hover: NinePatchTexture = self.ui_assets.get_window(9, 1)
        self.button_pressed: NinePatchTexture = self.ui_assets.get_window(9, 2)

        self.selected_map_path: Any = None

        self.anchor: arcade.gui.UIAnchorLayout = arcade.gui.UIAnchorLayout()
        self.add_widget(self.anchor)

        self.v_box: arcade.gui.UIBoxLayout = arcade.gui.UIBoxLayout(
            space_between=10)

        title_label: arcade.gui.UILabel = arcade.gui.UILabel(
            text="WELCOME, PLEASE CHOOSE THE MAP",
            font_name=KENNEY_FONT_NAME,
            font_size=36,
            text_color=arcade.color.COOL_BLACK,
            bold=False,
        )
        self.v_box.add(title_label.with_padding(bottom=30, top=12))

        map_dir: dict[Any, Any] = MapFolderManager().map_list

        category_order: dict[str, int] = {
            "easy": 0,
            "medium": 1,
            "hard": 2,
            "challenger": 3,
        }

        if not map_dir:
            empty_label: arcade.gui.UILabel = arcade.gui.UILabel(
                text="No maps found.",
                font_name=KENNEY_FONT_NAME,
                font_size=36,
                text_color=arcade.color.RED,
                bold=False
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
                map_name: str = map_info["name"]
                map_path: str = map_info["address"]
                normal_tex, hover_tex, pressed_tex = (
                    self.get_button_textures_by_category(map_info["category"])
                )

                button: arcade.gui.UITextureButton = (
                    arcade.gui.UITextureButton(
                        texture=normal_tex,
                        texture_hovered=hover_tex,
                        texture_pressed=pressed_tex,
                        text=map_name,
                        width=360,
                        height=36,
                        style={
                            "normal": arcade.gui.UITextureButton.UIStyle(
                                font_name=KENNEY_FONT_NAME,
                                font_size=24,
                                font_color=arcade.color.WHITE,
                            ),
                            "hover": arcade.gui.UITextureButton.UIStyle(
                                font_name=KENNEY_FONT_NAME,
                                font_size=24,
                                font_color=arcade.color.WHITE,
                            ),
                            "press": arcade.gui.UITextureButton.UIStyle(
                                font_name=KENNEY_FONT_NAME,
                                font_size=24,
                                font_color=arcade.color.BLACK,
                            ),
                            "disabled": arcade.gui.UITextureButton.UIStyle(
                                font_name=KENNEY_FONT_NAME,
                                font_size=24,
                                font_color=arcade.color.GRAY,
                            ),
                        },
                    ))

                button.on_click = self.make_map_handler(
                    map_name, map_path)
                self.v_box.add(button)

        self.anchor.add(
            child=self.v_box,
            anchor_x="center_x",
            anchor_y="center_y",
            align_y=0
        )

        quit_button: arcade.gui.UIFlatButton = arcade.gui.UIFlatButton(
            text="Quit",
            width=120,
        )
        quit_button.on_click = self.quit_game

        self.anchor.add(
            child=quit_button,
            anchor_x="right",
            anchor_y="top",
            align_x=-20,
            align_y=-20,
        )

    def make_map_handler(
            self,
            map_name: str,
            map_path: str
            ) -> Callable[[arcade.gui.UIOnClickEvent], None]:
        def on_click(event: arcade.gui.UIOnClickEvent) -> None:
            self.selected_map_path = map_path
            map_view: MapView = MapView(map_path=map_path, map_name=map_name)
            if self.window:
                self.window.show_view(map_view)

        return on_click

    def get_button_textures_by_category(
            self,
            category: str
            ) -> Tuple[NinePatchTexture, NinePatchTexture, NinePatchTexture]:
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

    def quit_game(self, event: arcade.gui.UIOnClickEvent) -> None:
        arcade.exit()

    def on_draw_before_ui(self) -> None:
        self.clear()

        center_x: float = self.window.width / 2
        center_y: float = self.window.height / 2

        main_rect: arcade.rect.Rect = arcade.XYWH(
            center_x, center_y, 800, 600)
        self.bg_panel.draw_rect(rect=main_rect)

        header_rect: arcade.rect.Rect = arcade.XYWH(
            center_x, center_y + 240, 600, 80)
        self.header_panel.draw_rect(rect=header_rect)
