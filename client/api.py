"""
API service for asynchronous communication with the server
using threads to avoid blocking the main Pygame loop
"""

import logging
import threading
import time
import uuid
from typing import Literal

import httpx

from core.models.network import RequestState

logger = logging.getLogger(__name__)


class APIClient:
    """Async API client for communication with the server."""

    def __init__(self, endpoint: str, use_ssl: bool, auth_token: str | None = None) -> None:
        """
        Initialize a new instance of the APIClient class.

        Args:
            endpoint: Base URL of the API
            use_ssl: Whether to use SSL
            auth_token: Authentication token
        """
        protocol = "https" if use_ssl else "http"
        self.client = httpx.Client(
            base_url=f"{protocol}://{endpoint}/api",
            headers={"User-Agent": "Pygame Client :D"},
        )
        self.auth_token = auth_token

        self.pending_requests: dict[str, RequestState] = {}

        # Lock para acesso thread-safe às respostas
        self.lock = threading.Lock()

    def set_auth_token(self, token: str | None) -> None:
        self.auth_token = token

    def _make_request(
        self, request_id: str, method: str, endpoint: str, data: dict | None, headers: dict | None
    ) -> None:
        """
        Do a request to the server on a separate thread

        Args:
            request_id: ID of the request
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API Endpoint
            data: Data to send
            headers: Headers to send
        """
        headers = headers or {}

        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        try:
            # Prepara a requisição
            if method == "GET":
                response = self.client.get(endpoint, headers=headers)
            elif method == "POST":
                response = self.client.post(endpoint, data=data, headers=headers)
            elif method == "PUT":
                response = self.client.put(endpoint, data=data, headers=headers)
            elif method == "DELETE":
                response = self.client.delete(endpoint, headers=headers)
            else:
                raise ValueError(f"Método HTTP não suportado: {method}")

            response.raise_for_status()

            result = RequestState(
                status="completed",
                timestamp=time.time(),
                success=True,
                data=response.json(),
            )

        except Exception as e:
            result = RequestState(
                status="completed",
                timestamp=time.time(),
                success=False,
                error={"message": str(e)},
            )

            logger.error(f"Unexpected error for {method} {endpoint}: {e}")

        with self.lock:
            self.pending_requests[request_id] = result

    def request(
        self,
        endpoint: str,
        method: Literal["GET", "POST", "PUT", "DELETE"],
        data: dict | None = None,
        headers: dict | None = None,
    ) -> str:
        request_id = str(uuid.uuid4())

        # Inicia thread para requisição
        thread = threading.Thread(
            target=self._make_request,
            args=(request_id, method, endpoint, data, headers),
        )
        thread.daemon = True
        thread.start()

        # Registra requisição pendente
        with self.lock:
            self.pending_requests[request_id] = RequestState(
                status="pending", timestamp=time.time()
            )

        return request_id

    def get_request_status(self, request_id: str) -> RequestState | None:
        """
        Check the status of a request.

        Args:
            request_id: ID of the request

        Returns:
            Request data or None if not found
        """
        with self.lock:
            return self.pending_requests.get(request_id)

    def remove_request(self, request_id: str) -> None:
        """
        Remove a request from the dictionary.

        Args:
            request_id: ID of the request
        """
        with self.lock:
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]

    def cleanup_old_requests(self, max_age_seconds: int = 300) -> None:
        """
        Remove old requests.

        Args:
            max_age_seconds: Maximum age in seconds
        """
        current_time = time.time()

        with self.lock:
            request_ids = list(self.pending_requests.keys())

            for request_id in request_ids:
                request = self.pending_requests[request_id]
                if current_time - request.timestamp > max_age_seconds:
                    del self.pending_requests[request_id]
