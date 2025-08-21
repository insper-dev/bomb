"""SSL configuration for PyInstaller builds."""

import os
import ssl
import sys


def get_ssl_context() -> ssl.SSLContext:
    """Get SSL context with proper certificate verification for PyInstaller builds."""
    context = ssl.create_default_context()

    # Check if we're running in a PyInstaller bundle
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # Running in PyInstaller bundle
        bundle_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))

        # Try multiple possible locations for the certificate bundle
        ca_bundle_paths = [
            os.path.join(bundle_dir, "cacert.pem"),
            os.path.join(bundle_dir, "certifi", "cacert.pem"),
        ]

        for ca_bundle in ca_bundle_paths:
            if os.path.exists(ca_bundle):
                context.load_verify_locations(ca_bundle)
                break
        else:
            # Fallback to system certificates if bundle not found
            pass

    return context


def configure_ssl_for_httpx() -> ...:
    """Configure SSL for httpx client."""
    import httpx

    # Get SSL context
    ssl_context = get_ssl_context()

    # Return httpx client with custom SSL context
    return httpx.Client(verify=ssl_context)


def get_websocket_ssl_context() -> ssl.SSLContext:
    """Get SSL context for websockets."""
    return get_ssl_context()
