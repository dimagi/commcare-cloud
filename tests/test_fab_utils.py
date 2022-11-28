from datetime import datetime
from nose.tools import assert_equal

from commcare_cloud.fab.utils import get_changelogs_in_date_range


def test_get_changelogs():
    def _get_file_content():
        return open("hosting_docs/source/changelog/index.md").read().split("\n")
    assert_equal(
        set(get_changelogs_in_date_range(datetime(2022, 11, 1), datetime(2022, 11, 11), _get_file_content)),
        {
            "https://commcare-cloud.readthedocs.io/en/latest/changelog/0063-backfill_sms_event_data_for_api_performance.html",
            "https://commcare-cloud.readthedocs.io/en/latest/changelog/0062-kafka-upgrade-to-3.2.3.html",
            "https://commcare-cloud.readthedocs.io/en/latest/changelog/0061-install-elasticsearch-phonetic-analysis-plugin.html",
            "https://commcare-cloud.readthedocs.io/en/latest/changelog/0060-upgrade-to-python-3-10.html",
            "https://commcare-cloud.readthedocs.io/en/latest/changelog/0059-postgres-v14-upgrade.html"
        }
    )