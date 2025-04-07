from core.abstract import App


class ServerApp(App):
    def run(self) -> None:
        print(f"Hello, World!\n\t{self.settings=}")
