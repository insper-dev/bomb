from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from prisma.partials import CurrentUser

from client.services.base import ServiceBase
from core.constants import SESSION_FILE
from core.models.network import RequestState


class AuthService(ServiceBase):
    """Gerencia login, signup, logout e fetch de usuário atual."""

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self.current_user: CurrentUser | None = None
        self.login_request_id: str | None = None
        self.signup_request_id: str | None = None
        self.logout_request_id: str | None = None
        self.get_current_user_request_id: str | None = None
        self.errors: dict[str, str | None] = {
            "login": None,
            "signup": None,
            "logout": None,
            "get_user": None,
        }
        self.on_login_success_callbacks: list[Callable[[str], Any]] = []
        self.on_login_error_callbacks: list[Callable[[str], Any]] = []
        self.on_logout_callbacks: list[Callable[[], Any]] = []

        self.__load_session()

    def __load_session(self) -> None:
        if SESSION_FILE.exists():
            try:
                with SESSION_FILE.open("r") as f:
                    data = json.load(f)
                    token = data["access_token"]
                    self.app.api_client.set_auth_token(token)
                    # já dispara GET /me para recuperar current_user
                    self.get_current_user()
            except (json.JSONDecodeError, KeyError):
                self.current_user = None
                SESSION_FILE.unlink(missing_ok=True)
        else:
            self.current_user = None

    def __save_session(self, access_token: str) -> None:
        with SESSION_FILE.open("w") as f:
            json.dump({"access_token": access_token}, f)

    def register_login_success_callback(self, cb: Callable[[str], Any]) -> None:
        self.on_login_success_callbacks.append(cb)

    def register_login_error_callback(self, cb: Callable[[str], Any]) -> None:
        self.on_login_error_callbacks.append(cb)

    def register_logout_callback(self, cb: Callable[[], Any]) -> None:
        self.on_logout_callbacks.append(cb)

    # ——— Status getters ———
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

    # ——— Propriedades de loading ———
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
        """Aguarda GET /me e só aí dispara o callback de sucesso."""
        status = self.get_current_user_status()
        if not status:
            return False
        if status.status == "completed":
            if status.success and status.data:
                # atualiza current_user
                self.current_user = CurrentUser.model_validate(status.data)
                # dispara só agora os callbacks de login/signup
                # o token já vai estar setado, mas só pra dar bypass no type:
                if self.app.api_client.auth_token:
                    for cb in self.on_login_success_callbacks:
                        try:
                            cb(self.app.api_client.auth_token)
                        except Exception as e:
                            print(f"Error in login success callback: {e}")
                else:
                    print("WARNING: Auth token not set [matrix error]")
            else:
                self.current_user = None
                self.errors["get_user"] = self._get_error_message(status)
            self.get_current_user_request_id = None
            return False
        return True  # pendente

    @property
    def is_logged_in(self) -> bool:
        return self.current_user is not None

    # ——— Métodos de ação ———
    def login(self, username: str, password: str) -> str:
        if self.is_login_loading:
            print("Login request already in progress.")
            return self.login_request_id or ""
        self.errors["login"] = None
        self.login_request_id = self.app.api_client.request(
            "/auth/login", "POST", {"username": username, "password": password}
        )
        return self.login_request_id

    def signup(self, username: str, password: str) -> str:
        if self.is_signup_loading:
            print("Signup request already in progress.")
            return self.signup_request_id or ""
        self.errors["signup"] = None
        self.signup_request_id = self.app.api_client.request(
            "/auth/signup",
            "POST",
            json={"username": username, "password": password},
            headers={"Content-Type": "application/json"},
        )
        return self.signup_request_id

    def logout(self) -> str:
        if self.is_logout_loading:
            print("Logout request already in progress.")
            return self.logout_request_id or ""
        self.logout_request_id = self.app.api_client.request("/auth/logout", "POST")
        self.app.api_client.set_auth_token(None)
        self.current_user = None
        SESSION_FILE.unlink(missing_ok=True)
        for cb in self.on_logout_callbacks:
            try:
                cb()
            except Exception as e:
                print(f"Error in logout callback: {e}")
        return self.logout_request_id

    def get_current_user(self) -> str:
        if self.is_current_user_loading:
            print("Get-current-user request already in progress.")
            return self.get_current_user_request_id or ""
        self.errors["get_user"] = None
        self.get_current_user_request_id = self.app.api_client.request("/auth/me", "GET")
        return self.get_current_user_request_id

    # ——— Erros ———
    def get_login_error(self) -> str | None:
        return self.errors["login"]

    def get_signup_error(self) -> str | None:
        return self.errors["signup"]

    def _handle_successful_login(self, data: dict[str, Any]) -> None:
        if "access_token" in data:
            token = data["access_token"]
            self.app.api_client.set_auth_token(token)
            self.__save_session(token)
            # só dispara GET /me; callback fica para is_current_user_loading
            self.get_current_user()

    def _handle_failed_login(self, status: RequestState) -> None:
        msg = self._get_error_message(status)
        self.errors["login"] = msg
        for cb in self.on_login_error_callbacks:
            try:
                cb(msg)
            except Exception as e:
                print(f"Error in login error callback: {e}")

    def _get_error_message(self, status: RequestState) -> str:
        if not status or not status.error:
            return "Unknown request error"
        err = status.error
        if "message" in err:
            return err["message"]
        if "detail" in err:
            return err["detail"]
        return str(err)
