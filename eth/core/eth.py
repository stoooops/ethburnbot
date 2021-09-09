import json
import time
from logging import getLogger
from typing import Any, Dict, List, Union

import requests

from eth.types.block import Block, UncleBlock

URL = "https://mainnet.infura.io/v3/"

LOG = getLogger(__name__)


class EthereumClient:
    def __init__(self, url: str):
        self._url = url

    def retry_post(self, data: Dict[str, Any], attempts: int = 10):
        backoff_sec = 1
        response = None
        for i in range(attempts):
            if i > 0:
                time.sleep(backoff_sec)

            response = requests.post(self._url, json=data)

            # parse JSON response
            if response.status_code != 200:
                LOG.error(
                    f"[Attempt: {i+1}] status code: {response.status_code}, reason: {response.status_code}"
                )

            else:
                response_json = json.loads(response.content)

                # read response
                if "error" in response_json:
                    code = response_json["error"]["code"]
                    message = response_json["error"]["message"]
                    LOG.error(f'Error code "{code}", message: "{message}"')

                elif "result" not in response_json:
                    LOG.error(f"Malformed response JSON missing 'result' field:")
                    LOG.error(f"{response_json}")
                else:
                    return response

            backoff_sec = backoff_sec * 1.5

        return response

    def _params(
        self, method: str, params: List[str]
    ) -> Dict[str, Union[str, int, List[str]]]:
        return {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}

    def eth_blockNumber(self) -> int:
        params = self._params("eth_blockNumber", [])
        r = self.retry_post(params)
        if r.status_code == 200:
            content_dict = json.loads(r.content)
            return int(content_dict["result"], 16)
        else:
            raise IOError(f"status code: {r.status_code}, reason: {r.status_code}")

    def eth_getBlockByNumber(self, num: int) -> Block:
        params = {
            "jsonrpc": "2.0",
            "method": "eth_getBlockByNumber",
            "params": [hex(num), False],
            "id": 1,
        }
        r = self.retry_post(params)
        if r.status_code == 200:
            block_dict = json.loads(r.content)
            if "baseFeePerGas" not in block_dict["result"]:
                LOG.error("Unexpected response:")
                LOG.error(f"{block_dict}")
            block = Block(block_dict["result"])
            return block
        else:
            raise IOError(f"status code: {r.status_code}, reason: {r.status_code}")

    def eth_getUncleCountByBlockNumber(self, num: int) -> int:
        params = {
            "jsonrpc": "2.0",
            "method": "eth_getUncleCountByBlockNumber",
            "params": [hex(num)],
            "id": 1,
        }
        r = self.retry_post(params)
        if r.status_code == 200:
            content_dict = json.loads(r.content)
            val: int = int(content_dict["result"], 16)
            return val
        else:
            raise IOError(f"status code: {r.status_code}, reason: {r.status_code}")

    def eth_getUncleByBlockNumberAndIndex(self, num: int, index) -> UncleBlock:
        params = self._params(
            "eth_getUncleByBlockNumberAndIndex", [hex(num), hex(index)]
        )
        r = self.retry_post(params)
        if r.status_code == 200:
            block_dict = json.loads(r.content)
            try:
                block = UncleBlock(block_dict["result"], num, index)
            except:
                LOG.error("Could not create UncleBlock object")
                LOG.error(json.dumps(block_dict, indent=4))
                raise
            return block
        else:
            raise IOError(f"status code: {r.status_code}, reason: {r.status_code}")


class InfuraClient(EthereumClient):
    def __init__(self, project_id: str):
        super().__init__(f"{URL}{project_id}")


class GethClient(EthereumClient):
    def __init__(self, ip_addr: str = "localhost", port: int = 8545):
        super().__init__(f"http://{ip_addr}:{port}")
