from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from client.app import ClientApp


class ServiceBase:
    def __init__(self, app: "ClientApp") -> None:
        self.app = app
