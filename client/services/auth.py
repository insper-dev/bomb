from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from prisma.partials import CurrentUser

from client.services.base import ServiceBase
from core.constants import SESSION_FILE
from core.models.network import RequestState


class AuthService(ServiceBase):
    current_user: CurrentUser | None
    login_request_id: str | None
    signup_request_id: str | None
    logout_request_id: str | None
    get_current_user_request_id: str | None
    errors: dict[str, str | None]
    on_login_success_callbacks: list[Callable[[str], Any]]
    on_login_error_callbacks: list[Callable[[str], Any]]
    on_logout_callbacks: list[Callable[[], Any]]

    def __init__(self, *args) -> None:
        super().__init__(*args)

        self.current_user = None
        self.login_request_id = None
        self.signup_request_id = None
        self.logout_request_id = None
        self.get_current_user_request_id = None

        self.errors = {
            "login": None,
            "signup": None,
            "logout": None,
            "get_user": None,
        }

        self.on_login_success_callbacks = []
        self.on_login_error_callbacks = []
        self.on_logout_callbacks = []

        self.__load_session()

    def __load_session(self) -> None:
        if SESSION_FILE.exists():
            try:
                with SESSION_FILE.open("r") as f:
                    session_data = json.load(f)
                    self.app.api_client.set_auth_token(session_data["access_token"])
                    self.get_current_user()
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Erro ao carregar sessão: {e}")
                self.current_user = None
                SESSION_FILE.unlink(missing_ok=True)
        else:
            self.current_user = None

    def __save_session(self, access_token: str) -> None:
        with SESSION_FILE.open("w") as f:
            json.dump({"access_token": access_token}, f)

    def register_login_success_callback(self, callback: Callable[[str], Any]) -> None:
        self.on_login_success_callbacks.append(callback)

    def register_login_error_callback(self, callback: Callable[[str], Any]) -> None:
        self.on_login_error_callbacks.append(callback)

    def register_logout_callback(self, callback: Callable[[], Any]) -> None:
        self.on_logout_callbacks.append(callback)

    def get_login_status(self) -> RequestState | None:
        return (
            self.app.api_client.get_request_status(self.login_request_id)
            if self.login_request_id
            else None
        )

    def get_signup_status(self) -> RequestState | None:
        return (
            self.app.api_client.get_request_status(self.signup_request_id)
            if self.signup_request_id
            else None
        )

    def get_logout_status(self) -> RequestState | None:
        return (
            self.app.api_client.get_request_status(self.logout_request_id)
            if self.logout_request_id
            else None
        )

    def get_current_user_status(self) -> RequestState | None:
        return (
            self.app.api_client.get_request_status(self.get_current_user_request_id)
            if self.get_current_user_request_id
            else None
        )

    @property
    def is_login_loading(self) -> bool:
        status = self.get_login_status()
        if not status:
            return False
        if status.status == "completed":
            if status.success and status.data:
                self._handle_successful_login(status.data)
            else:
                self._handle_failed_login(status)
            self.login_request_id = None
            return False
        return status.status == "pending"

    @property
    def is_signup_loading(self) -> bool:
        status = self.get_signup_status()
        if not status:
            return False
        if status.status == "completed":
            if status.success and status.data:
                self._handle_successful_login(status.data)
            else:
                self.errors["signup"] = self._get_error_message(status)
            self.signup_request_id = None
            return False
        return status.status == "pending"

    @property
    def is_logout_loading(self) -> bool:
        status = self.get_logout_status()
        if not status:
            return False
        if status.status == "completed":
            self.logout_request_id = None
            return False
        return status.status == "pending"

    @property
    def is_current_user_loading(self) -> bool:
        status = self.get_current_user_status()
        if not status:
            return False
        if status.status == "completed":
            if status.success and status.data:
                self.current_user = CurrentUser.model_validate(status.data)
            else:
                self.current_user = None
                self.errors["get_user"] = self._get_error_message(status)
            self.get_current_user_request_id = None
            return False
        return status.status == "pending"

    @property
    def is_logged_in(self) -> bool:
        return self.current_user is not None

    def login(self, username: str, password: str) -> str:
        if self.is_login_loading:
            print("Uma requisição de login já está em andamento.")
            return self.login_request_id or ""

        self.errors["login"] = None
        self.login_request_id = self.app.api_client.request(
            "/auth/login", "POST", {"username": username, "password": password}
        )
        return self.login_request_id

    def signup(self, username: str, password: str) -> str:
        if self.is_signup_loading:
            print("Uma requisição de signup já está em andamento.")
            return self.signup_request_id or ""

        self.errors["signup"] = None
        self.signup_request_id = self.app.api_client.request(
            "/auth/signup", "POST", {"username": username, "password": password}
        )
        return self.signup_request_id

    def logout(self) -> str:
        if self.is_logout_loading:
            print("Uma requisição de logout já está em andamento.")
            return self.logout_request_id or ""

        self.logout_request_id = self.app.api_client.request("/auth/logout", "POST")
        self.app.api_client.set_auth_token(None)
        self.current_user = None
        SESSION_FILE.unlink(missing_ok=True)

        for callback in self.on_logout_callbacks:
            try:
                callback()
            except Exception as e:
                print(f"Erro em callback de logout: {e}")

        return self.logout_request_id

    def get_current_user(self) -> str:
        if self.is_current_user_loading:
            print("Uma requisição de current user já está em andamento.")
            return self.get_current_user_request_id or ""

        self.errors["get_user"] = None
        self.get_current_user_request_id = self.app.api_client.request("/auth/me", "GET")
        return self.get_current_user_request_id

    def get_login_error(self) -> str | None:
        return self.errors["login"]

    def get_signup_error(self) -> str | None:
        return self.errors["signup"]

    def _handle_successful_login(self, data: dict[str, Any]) -> None:
        if "access_token" in data:
            access_token = data["access_token"]
            self.app.api_client.set_auth_token(access_token)
            self.__save_session(access_token)
            self.get_current_user()
            for callback in self.on_login_success_callbacks:
                try:
                    callback(access_token)
                except Exception as e:
                    print(f"Erro em callback de login bem-sucedido: {e}")

    def _handle_failed_login(self, status: RequestState) -> None:
        error_message = self._get_error_message(status)
        self.errors["login"] = error_message
        for callback in self.on_login_error_callbacks:
            try:
                callback(error_message)
            except Exception as e:
                print(f"Erro em callback de login falho: {e}")

    def _get_error_message(self, status: RequestState) -> str:
        if not status or not status.error:
            return "Erro desconhecido na requisição"
        if "message" in status.error:
            return status.error["message"]
        if "detail" in status.error:
            return status.error["detail"]
        return str(status.error)
