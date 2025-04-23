import argparse

from icecream import ic

from core.abstract import App
from core.config import get_settings


def main() -> None:
    # TODO: desabilitar icecream de acordo com argumento CLI
    ic.configureOutput(prefix="🍦 DEBUG | ")
    parser = argparse.ArgumentParser(description="Bomberman Online - Cliente/Servidor")

    parser.add_argument(
        "--mode",
        "-m",
        choices=["client", "server"],
        default="client",
        help="Modo de execução: 'client' ou 'server' (padrão: client)",
    )
    args = parser.parse_args()

    app_cls: type[App] | None = None
    if args.mode == "client":
        from client.app import ClientApp

        app_cls = ClientApp
    elif args.mode == "server":
        from server.app import ServerApp

        app_cls = ServerApp

    if app_cls is not None:
        app = app_cls(get_settings())
        app.run()


if __name__ == "__main__":
    main()
