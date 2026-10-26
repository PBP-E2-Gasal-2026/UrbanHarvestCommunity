"""Cancellable provider I/O, including responses that never finish a chunk.

Requests' read timeout only bounds inactivity. A short-lived spawned process lets
the coordinator enforce a total deadline without leaving blocked I/O threads.
The child never receives database connections or Django model objects.
"""

import multiprocessing
import time

import requests


def _post_worker(sender, url, kwargs):
    response = None
    try:
        kwargs["stream"] = True
        response = requests.post(url, **kwargs)
        body = bytearray()
        for chunk in response.iter_content(chunk_size=8192):
            body.extend(chunk)
            if len(body) > 65536:
                raise ValueError("Provider response exceeds limit")
        sender.send(("ok", response.status_code, bytes(body)))
    except Exception:  # noqa: BLE001 - sanitize the isolated network boundary
        sender.send(("error", None, b""))
    finally:
        if response is not None:
            response.close()
        sender.close()


def bounded_post(url, *, deadline_seconds=35, **kwargs):
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(
        target=_post_worker,
        args=(sender, url, kwargs),
        name="llm-provider-request",
        daemon=True,
    )
    started = time.monotonic()
    try:
        process.start()
        sender.close()
        remaining = max(0, deadline_seconds - (time.monotonic() - started))
        if not receiver.poll(remaining):
            raise requests.Timeout("Provider total deadline exceeded")
        outcome, status, body = receiver.recv()
        if outcome != "ok":
            raise requests.ConnectionError("Provider request failed")
        response = requests.Response()
        response.status_code = status
        response._content = body
        response._content_consumed = True
        return response
    except requests.RequestException:
        raise
    except (OSError, EOFError, RuntimeError) as exc:
        raise requests.ConnectionError("Provider process unavailable") from exc
    finally:
        sender.close()
        receiver.close()
        if process.pid is not None:
            if process.is_alive():
                process.terminate()
            process.join(timeout=1)
            if process.is_alive():
                process.kill()
                process.join(timeout=1)
            process.close()
