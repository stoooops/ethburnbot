import os
import shutil
from logging import getLogger

from eth.utils.file_utils import pending_tweets_filepaths, tweeted_tweets_dir
from potpourri.python.twitter.client import TwitterClient, make_twitter_client

LOG = getLogger(__name__)


class Tweeter:
    def __init__(self):
        self._client: TwitterClient = make_twitter_client(
            secrets_json_filepath="/app/data/secrets/twitter.json"
        )

    def process(self, dry_run: bool = False) -> bool:
        tweeted = False
        for pending_tweet_filepath in pending_tweets_filepaths():
            with open(pending_tweet_filepath, "r") as f:
                tweet = str(f.read())
                LOG.info("Tweeting:")
                LOG.info("\n" + tweet)
                tweeted = True

                if not dry_run:
                    self._client.tweet(tweet)

            if not dry_run:
                tweeted_filepath = os.path.join(
                    tweeted_tweets_dir(), os.path.basename(pending_tweet_filepath)
                )
                shutil.move(pending_tweet_filepath, tweeted_filepath)

            # only process one
            return tweeted

        return tweeted
