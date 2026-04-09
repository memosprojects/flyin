from .welcome_page import WelcomeView
import arcade


def main() -> None:
    SCREEN_WIDTH = 1280
    SCREEN_HEIGHT = 780
    SCREEN_TITLE = "Flyin - Welcome"

    window = arcade.Window(
        SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, fullscreen=True
    )

    welcome_view = WelcomeView()
    window.show_view(welcome_view)
    arcade.run()


if __name__ == "__main__":
    main()
