from client.services.base import ServiceBase


class AuthService(ServiceBase):
    current_user: ...

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.__login_request_id: str | None = None
        self.__signup_request_id: str | None = None
        self.__logout_request_id: str | None = None
        self.__get_current_user_request_id: str | None = None

    @property
    def is_login_loading(self) -> bool:
        if self.__login_request_id is None:
            return False

        request_status = self.app.api_client.get_request_status(self.__login_request_id)

        if request_status is None:
            return False

        if request_status.data is not None:
            self.app.api_client.set_auth_token(request_status.data["access_token"])

        return request_status.status == "pending"

    def login(self, username: str, password: str) -> None:
        if self.is_login_loading:
            # TODO: move to logging.warn (dev level)
            print("A requisição de login ainda está em andamento.")
            return
        self.__login_request_id = self.app.api_client.request(
            "/auth/login", "POST", {"username": username, "password": password}
        )

    # TODO: implement the rest
    def signup(self, username: str, password: str) -> None: ...

    def logout(self) -> None: ...

    def get_current_user(self) -> None: ...
