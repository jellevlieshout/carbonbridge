import asyncio
import json
import urllib.request
import urllib.error
from typing import Any, Dict, Optional

async def request(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    timeout: float = 10.0,
) -> Any:
    """
    Executes an HTTP request asynchronously using a thread executor.
    """
    if headers is None:
        headers = {}
    
    data = None
    if json_data is not None:
        data = json.dumps(json_data).encode("utf-8")
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"
    
    # Ensure we always accept JSON
    if "Accept" not in headers:
        headers["Accept"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    
    loop = asyncio.get_running_loop()
    
    return await loop.run_in_executor(None, _perform_request, req, timeout)

def _perform_request(req: urllib.request.Request, timeout: float) -> Any:
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            response_data = response.read()
            if not response_data:
                return None
            return json.loads(response_data)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        try:
            error_json = json.loads(error_body)
            # Re-raising with the parsed error structure if possible
            raise Exception(f"HTTP Error {e.code}: {json.dumps(error_json)}") from e
        except json.JSONDecodeError:
            raise Exception(f"HTTP Error {e.code}: {error_body}") from e
    except Exception as e:
        raise e
