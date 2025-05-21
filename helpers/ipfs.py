import json
import os

import httpx

ALGOKIT_PINATA_JWT = "ALGOKIT_PINATA_JWT"

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
DEFAULT_TIMEOUT = 90


class PinataError(Exception):
    """Base class for Piñata errors."""

    def __init__(self, response: httpx.Response):
        self.response = response
        super().__init__(f"Pinata error: {response.status_code}")

    def __str__(self) -> str:
        return f"Pinata error: {self.response.status_code}. {self.response.text}"


class PinataBadRequestError(PinataError):
    pass


class PinataUnauthorizedError(PinataError):
    pass


class PinataForbiddenError(PinataError):
    pass


class PinataInternalServerError(PinataError):
    pass


class PinataHttpError(PinataError):
    pass


def get_pinata_jwt() -> str:
    """
    Retrieves an API key from the ALGOKIT_PINATA_JWT environment variable.

    Returns:
        str | None: The retrieved JWT, or None if no environment variable is found.
    """
    try:
        return os.environ[ALGOKIT_PINATA_JWT]
    except KeyError as err:
        raise err


def upload_to_pinata(json_data: dict[str, object], jwt: str) -> str:
    """
    Uploads a JSON to the Piñata API.

    Args:
        json_data (dict): JSON data to be uploaded.
        jwt (str): The JWT for accessing the Piñata API.

    Returns:
        str: The CID (Content Identifier) of the uploaded file.

    Raises:
        ValueError: If the CID is not a string.
        PinataBadRequestError: If there is a bad request error.
        PinataUnauthorizedError: If there is an unauthorized error.
        PinataForbiddenError: If there is a forbidden error.
        PinataInternalServerError: If there is an internal server error.
        PinataHttpError: If there is an HTTP error.

    Example Usage:
        json_data = {"name": "Alice", "level": 2}
        jwt = "your_jwt"

        cid = upload_to_pinata(json_data, jwt)
        print(cid) # e.g. "bafybeih6z7z2z3z4z5z6z7z8z9z0"
    """

    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {jwt}",
    }

    pinata_options = {"cidVersion": 1}
    data = {"pinataOptions": json.dumps(pinata_options)}
    try:
        response = httpx.post(
            url="https://api.pinata.cloud/pinning/pinFileToIPFS",
            data=data,
            json=json.dumps(json_data),
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
        )

        response.raise_for_status()
        cid = response.json().get("IpfsHash")  # type: ignore
        if not isinstance(cid, str):  # type: ignore
            raise ValueError("IpfsHash is not a string.")
        return cid
    except httpx.HTTPStatusError as ex:
        if ex.response.status_code == httpx.codes.BAD_REQUEST:
            raise PinataBadRequestError(ex.response) from ex
        if ex.response.status_code == httpx.codes.UNAUTHORIZED:
            raise PinataUnauthorizedError(ex.response) from ex
        if ex.response.status_code == httpx.codes.FORBIDDEN:
            raise PinataForbiddenError(ex.response) from ex
        if ex.response.status_code == httpx.codes.INTERNAL_SERVER_ERROR:
            raise PinataInternalServerError(ex.response) from ex

        raise PinataHttpError(ex.response) from ex
