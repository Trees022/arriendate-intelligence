import asyncio
import os
import sys

import uvicorn


def compatible_event_loop() -> asyncio.AbstractEventLoop:
    """Use the selector loop required by psycopg async on Windows."""
    if sys.platform == "win32":
        return asyncio.SelectorEventLoop()
    return asyncio.new_event_loop()


def main() -> None:
    """Run the API with a cross-platform loop compatible with PostgreSQL."""
    loop = compatible_event_loop if sys.platform == "win32" else "auto"
    uvicorn.run(
        os.getenv("ARRIENDATE_ASGI_APP", "app.main:app"),
        host=os.getenv("ARRIENDATE_API_HOST", "127.0.0.1"),
        port=int(os.getenv("ARRIENDATE_API_PORT", "8000")),
        reload=os.getenv("ARRIENDATE_API_RELOAD", "false").lower() == "true",
        # Uvicorn accepts a loop factory at runtime, but its public annotation lists literals only.
        loop=loop,  # type: ignore[arg-type]
        app_dir=os.getenv("ARRIENDATE_APP_DIR"),
    )


if __name__ == "__main__":
    main()
