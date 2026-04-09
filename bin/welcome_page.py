import arcade
import arcade.gui
from pathlib import Path
from typing import TypedDict
from arcade.gui import NinePatchTexture, UIView
from .map_manager import MapFolderManager
from .map_page import MapView


class MapInfo(TypedDict):
    '''Typed dictionary describing metadata for a map entry.

    Attributes:
        name (str): Human-readable map name.
        address (str): File path to the map.
        category (str): Difficulty category of the map.
        number (int): Ordering index within the category.
    '''
    name: str
    address: str
    category: str
    number: int


class UIAssets:
    '''Load and provide UI textures used across the welcome screen.

    This class centralizes texture loading and creation of UI elements
    such as NinePatch windows and button textures.
    '''
    def __init__(self) -> None:
        '''Load the UI sprite sheet and prepare texture grid.'''
        path_to_ui: Path = (
            Path(__file__).parent
            / ".."
            / "uilibrary"
            / "tilemap_packed.png"
        ).resolve()
        sheet: arcade.SpriteSheet = arcade.load_spritesheet(path_to_ui)
        self.textures: list[arcade.Texture] = sheet.get_texture_grid(
            size=(32, 32),
            columns=13,
            count=91,
        )

    def get_window(self,
                   col: int,
                   row: int,
                   border: int = 5
                   ) -> NinePatchTexture:
        '''Create a NinePatchTexture window from the sprite sheet.

        Args:
            col (int): Column index in the texture grid.
            row (int): Row index in the texture grid.
            border (int): Border size for scaling.

        Returns:
            NinePatchTexture: Scalable UI window texture.
        '''
        texture: arcade.Texture = self.textures[row * 13 + col]
        return NinePatchTexture(
            left=border,
            right=border,
            bottom=border,
            top=border,
            texture=texture,
        )

    def get_texture(self, col: int, row: int) -> arcade.Texture:
        '''Retrieve a raw texture from the sprite grid.

        Args:
            col (int): Column index.
            row (int): Row index.

        Returns:
            arcade.Texture: Selected texture.
        '''
        return self.textures[row * 13 + col]


class WelcomeView(UIView):
    '''Render the welcome screen and allow map selection.

    This view builds the UI layout, lists available maps, and
    transitions to the map view upon user selection.
    '''
    def __init__(self) -> None:
        '''Initialize UI elements, load maps, and create selection buttons.'''
        super().__init__()
        KENNEY_FONT_PATH: str = ':resources:/fonts/ttf/Kenney/Kenney_Pixel.ttf'
        KENNEY_FONT_NAME: str = "Kenney Pixel"
        arcade.load_font(KENNEY_FONT_PATH)
        self.ui_assets: UIAssets = UIAssets()

        self.bg_panel: NinePatchTexture = self.ui_assets.get_window(0, 0)
        self.header_panel: NinePatchTexture = self.ui_assets.get_window(2, 0)

        self.selected_map_path: str | None = None

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

        map_dir: dict[str, MapInfo] = MapFolderManager().map_list

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
                    self.get_button_textures_by_category(
                        map_info["category"]
                    )
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

                @button.event("on_click")
                def on_click_map(event: arcade.gui.UIOnClickEvent,
                                 current_map_path: str = map_path,
                                 current_map_name: str = map_name) -> None:
                    self.selected_map_path = current_map_path
                    map_view: MapView = MapView(
                        map_path=current_map_path,
                        map_name=current_map_name,
                    )
                    if self.window:
                        self.window.show_view(map_view)

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

        @quit_button.event("on_click")
        def on_click_quit(event: arcade.gui.UIOnClickEvent) -> None:
            arcade.exit()

        self.anchor.add(
            child=quit_button,
            anchor_x="right",
            anchor_y="top",
            align_x=-20,
            align_y=-20,
        )

    def get_button_textures_by_category(
            self,
            category: str
            ) -> tuple[NinePatchTexture, NinePatchTexture, NinePatchTexture]:
        '''Return button textures based on map difficulty category.

        Args:
            category (str): Difficulty category of the map.

        Returns:
            tuple[NinePatchTexture, NinePatchTexture, NinePatchTexture]:
                Normal, hover, and pressed textures.
        '''
        normal_tex: NinePatchTexture = self.ui_assets.get_window(
            5, 0, border=6)
        if category == "easy":
            return (
                normal_tex,
                self.ui_assets.get_window(9, 1, border=6),
                self.ui_assets.get_window(9, 2, border=6),
            )
        if category == "medium":
            return (
                normal_tex,
                self.ui_assets.get_window(8, 1, border=6),
                self.ui_assets.get_window(7, 2, border=6),
            )
        if category == "hard":
            return (
                normal_tex,
                self.ui_assets.get_window(7, 1, border=6),
                self.ui_assets.get_window(5, 2, border=6),
            )
        return (
            normal_tex,
            self.ui_assets.get_window(7, 2, border=6),
            self.ui_assets.get_window(9, 2, border=6),
        )

    def on_draw_before_ui(self) -> None:
        '''Draw background panels before UI elements are rendered.

        Returns:
            None
        '''
        self.clear()

        center_x: float = self.window.width / 2
        center_y: float = self.window.height / 2

        main_rect: arcade.rect.Rect = arcade.XYWH(
            center_x, center_y, 800, 600)
        self.bg_panel.draw_rect(rect=main_rect)

        header_rect: arcade.rect.Rect = arcade.XYWH(
            center_x, center_y + 240, 600, 80)
        self.header_panel.draw_rect(rect=header_rect)
