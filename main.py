import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Bomberman Online - Cliente/Servidor")

    parser.add_argument(
        "--mode",
        "-m",
        choices=["client", "server"],
        default="client",
        help="Modo de execução: 'client' ou 'server' (padrão: client)",
    )
    args = parser.parse_args()

    apps = {
        "client": "client.app:main",
        "server": "server.app:main",
    }

    app = apps.get(args.mode)
    if app is None:
        raise ValueError(f"Modo inválido: {args.mode}. Use 'client' ou 'server'.")

    # import the module and function dynamically
    module_name, function_name = app.split(":")
    module = __import__(module_name, fromlist=[function_name])
    function = getattr(module, function_name)
    function()


if __name__ == "__main__":
    main()
