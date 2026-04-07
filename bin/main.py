from welcomepage import WelcomeView
import arcade


def main():
    SCREEN_WIDTH = 1920
    SCREEN_HEIGHT = 960
    SCREEN_TITLE = "Flyin - Welcome"

    window = arcade.Window(
        SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, fullscreen=False
    )
    welcome_view = WelcomeView()
    window.show_view(welcome_view)
    arcade.run()


if __name__ == "__main__":
    main()
