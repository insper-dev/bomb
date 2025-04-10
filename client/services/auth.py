import json

from prisma.partials import CurrentUser

from client.services.base import ServiceBase
from core.constants import SESSION_FILE


class AuthService(ServiceBase):
    current_user: CurrentUser | None = None

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.__login_request_id: str | None = None
        self.__signup_request_id: str | None = None
        self.__logout_request_id: str | None = None
        self.__get_current_user_request_id: str | None = None

        self.__load_session()

    def __load_session(self) -> None:
        if SESSION_FILE.exists():
            with SESSION_FILE.open("r") as f:
                session_data = json.load(f)
                self.app.api_client.set_auth_token(session_data["access_token"])
                self.get_current_user()
        else:
            self.current_user = None

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

    @property
    def is_signup_loading(self) -> bool:
        if self.__signup_request_id is None:
            return False

        request_status = self.app.api_client.get_request_status(self.__signup_request_id)

        if request_status is None:
            return False

        if request_status.data is not None:
            self.app.api_client.set_auth_token(request_status.data["access_token"])

        return request_status.status == "pending"

    @property
    def is_logout_loading(self) -> bool:
        if self.__logout_request_id is None:
            return False

        request_status = self.app.api_client.get_request_status(self.__logout_request_id)

        if request_status is None:
            return False

        return request_status.status == "pending"

    @property
    def is_current_user_loading(self) -> bool:
        if self.__get_current_user_request_id is None:
            return False

        request_status = self.app.api_client.get_request_status(self.__get_current_user_request_id)

        if request_status is None:
            return False

        if request_status.data is not None:
            self.current_user = CurrentUser.model_validate(request_status.data)
        else:
            self.current_user = None

        return request_status.status == "pending"

    def login(self, username: str, password: str) -> None:
        if self.is_login_loading:
            # TODO: move to logging.warn (dev level)
            print("A requisição de login ainda está em andamento.")
            return
        self.__login_request_id = self.app.api_client.request(
            "/auth/login", "POST", {"username": username, "password": password}
        )

    def signup(self, username: str, password: str) -> None:
        if self.is_signup_loading:
            print("A requisição de signup ainda está em andamento.")
            return
        self.__signup_request_id = self.app.api_client.request(
            "/auth/signup", "POST", {"username": username, "password": password}
        )

    def logout(self) -> None:
        if self.is_logout_loading:
            print("A requisição de logout ainda está em andamento.")
            return
        self.__logout_request_id = self.app.api_client.request("/auth/logout", "POST")
        self.app.api_client.set_auth_token(None)
        self.current_user = None

    def get_current_user(self) -> None:
        if self.is_current_user_loading:
            print("A requisição de current user ainda está em andamento.")
            return
        self.__get_current_user_request_id = self.app.api_client.request("/auth/me", "GET")
