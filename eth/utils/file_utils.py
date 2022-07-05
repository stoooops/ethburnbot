import os
from pathlib import Path
from typing import List


def root_dir() -> str:
    return os.path.normpath(os.path.join(Path(__file__).parent.resolve(), "../.."))


def data_dir() -> str:
    return os.path.join(root_dir(), "data")


def blocks_dir() -> str:
    return os.path.join(data_dir(), "blocks")


def block_filepath(num: int) -> str:
    return os.path.join(blocks_dir(), f"{num}.json")


def uncle_block_filepath(num: int, uncle_index: int) -> str:
    return block_filepath(num).replace(".json", f"_uncle{uncle_index}.json")


def tweets_dir() -> str:
    return os.path.join(data_dir(), "tweets")


def pending_tweets_dir() -> str:
    return os.path.join(tweets_dir(), "pending")


def pending_tweets_filepaths(ext: str = "") -> List[str]:
    return list(
        sorted(
            [
                os.path.join(pending_tweets_dir(), f)
                for f in next(os.walk(pending_tweets_dir()), (None, None, []))[2]
                if ext == "" or f.endswith(ext)
            ]
        )
    )


def tweeted_tweets_dir() -> str:
    result = os.path.join(tweets_dir(), "tweeted")
    os.makedirs(result, exist_ok=True)
    return result
