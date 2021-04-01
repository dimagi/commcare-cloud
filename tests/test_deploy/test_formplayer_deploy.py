import inspect

import requests_mock
from nose.tools import assert_equals, assert_is_none

from commcare_cloud.commands.deploy.formplayer import (
    get_latest_formplayer_version, get_info_urls, VersionInfo, strip_escapes
)

COMMIT = "e0b6d9251e6e92a26db0d765f6f276ae00a4df50"
MESSAGE = "Merge pull request \\#945 from dimagi/bounty"
TIME = "2021-03-31T14\\:38\\:18+0200"
BUILD_TIME = "2021-03-31T13\\:18\\:11.354Z"

EXAMPLE_GIT_PROPERTIES = inspect.cleandoc(f"""
    git.branch=master
    git.build.host=kamino1
    git.build.user.email=boba@theempire.com
    git.build.user.name=Boba Fett
    git.build.version=unspecified
    git.closest.tag.commit.count=
    git.closest.tag.name=
    git.commit.id={COMMIT}
    git.commit.id.abbrev=e0b6d92
    git.commit.id.describe=
    git.commit.message.full=Merge pull request \\#945 from dimagi/bounty-hunter\\n\\nbounty hunter training
    git.commit.message.short={MESSAGE}
    git.commit.time={TIME}
    git.commit.user.email=boba@theempire.com
    git.commit.user.name=Boba Fett
    git.dirty=true
    git.remote.origin.url=git@github.com\\:dimagi/formplayer.git
    git.tags=
    git.total.commit.count=3905
    """)

EXAMPLE_BUILD_PROPERTIES = inspect.cleandoc(f"""
    build.artifact=formplayer
    build.group=org.commcare
    build.name=Formplayer
    build.time={BUILD_TIME}
    build.version=2021-03-31 15\\:18\\:11
    """)


def test_get_latest_formplayer_version():
    git_info_url, build_info_url = get_info_urls("env1")
    with requests_mock.Mocker() as m:
        m.get(git_info_url, text=EXAMPLE_GIT_PROPERTIES)
        m.get(build_info_url, text=EXAMPLE_BUILD_PROPERTIES)
        version = get_latest_formplayer_version("env1")

    assert_equals(version, VersionInfo(
        commit=COMMIT,
        message=strip_escapes(MESSAGE),
        time=strip_escapes(TIME),
        build_time=strip_escapes(BUILD_TIME),
    ))


def test_get_latest_formplayer_version_error():
    git_info_url, build_info_url = get_info_urls("env1")
    with requests_mock.Mocker() as m:
        m.get(git_info_url, status_code=404)
        version = get_latest_formplayer_version("env1")

    assert_is_none(version)
