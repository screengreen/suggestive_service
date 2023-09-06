import os
from urllib.parse import urlencode

import requests


BASE_URL = "https://cloud-api.yandex.net/v1/disk/public/resources/download?"


def download_yandex_disk(url: str, output_path: str) -> None:
    """Download data from Yandex Disk

    Args:
        url (str): Public data URL from Yandex Disk
        output_path (str): Output path to save downloaded data

    Raises:
        Exception: Dataset cannot be downloaded
    """
    if os.path.exists(output_path):
        print(f"Output file {output_path} already exists!")
        return

    try:
        # Getting a full link
        full_url = BASE_URL + urlencode(dict(public_key=url))
        response = requests.get(full_url)
        download_url = response.json()["href"]

        # Save response to file
        download_response = requests.get(download_url)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as output_file:
            output_file.write(download_response.content)
    except Exception as e:
        raise Exception("Dataset cannot be downloaded") from e
