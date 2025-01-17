from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import PropertyMock, patch

import pytest
from shared.reports.readonly import ReadOnlyReport
from shared.reports.resources import Report, ReportFile
from shared.reports.types import Change, LineSession, ReportLine, ReportTotals
from shared.torngit.exceptions import (
    TorngitClientError,
    TorngitClientGeneralError,
    TorngitObjectNotFoundError,
    TorngitServerUnreachableError,
)
from shared.utils.sessions import Session
from shared.yaml import UserYaml

import services.notification.notifiers.mixins.message.sections as sections
from database.tests.factories import RepositoryFactory
from services.comparison.overlays.critical_path import CriticalPathOverlay
from services.decoration import Decoration
from services.notification.notifiers.base import NotificationResult
from services.notification.notifiers.comment import CommentNotifier
from services.notification.notifiers.mixins.message.helpers import (
    diff_to_string,
    format_number_to_str,
    sort_by_importance,
)
from services.notification.notifiers.mixins.message.sections import (
    AnnouncementSectionWriter,
    ComponentsSectionWriter,
    FileSectionWriter,
    ImpactedEntrypointsSectionWriter,
    NewFilesSectionWriter,
    NewFooterSectionWriter,
    NewHeaderSectionWriter,
)
from services.notification.notifiers.tests.conftest import generate_sample_comparison
from services.yaml.reader import get_components_from_yaml


@pytest.fixture
def is_not_first_pull(mocker):
    mocker.patch(
        "database.models.core.Pull.is_first_pull",
        return_value=False,
        new_callable=PropertyMock,
    )


@pytest.fixture
def sample_comparison_bunch_empty_flags(request, dbsession, mocker):
    """
    This is what this fixture has regarding to flags
    - first is on both reports, both with 100% coverage (the common already existing result)
    - second is declared on both reports, but is only on the head report, with 50% coverage
    - third is declared on both reports, but only has coverage information on the base report,
    with 50% coverage
    - fourth is declared on both reports, and has no coverage information anywhere
    - fifthis only declared at the head report, but has no coverage information there
    - sixth is only declared at the head report, and has information: 100% coverage there
    - seventh is only declared at the base report, but has no coverage information there
    - eighth is only declared at the base report, and has 100% coverage there
    """
    head_report = Report()
    head_report.add_session(Session(flags=["first"]))
    head_report.add_session(Session(flags=["second"]))
    head_report.add_session(Session(flags=["third"]))
    head_report.add_session(Session(flags=["fourth"]))
    head_report.add_session(Session(flags=["fifth"]))
    head_report.add_session(Session(flags=["sixth"]))
    base_report = Report()
    base_report.add_session(Session(flags=["first"]))
    base_report.add_session(Session(flags=["second"]))
    base_report.add_session(Session(flags=["third"]))
    base_report.add_session(Session(flags=["fourth"]))
    base_report.add_session(Session(flags=["seventh"]))
    base_report.add_session(Session(flags=["eighth"]))
    print(base_report.sessions)
    # assert False
    file_1 = ReportFile("space.py")
    file_1.append(
        1,
        ReportLine.create(
            coverage=1, sessions=[LineSession(0, 1), LineSession(1, "1/2")]
        ),
    )
    file_1.append(
        40,
        ReportLine.create(coverage=1, sessions=[LineSession(5, 1), LineSession(1, 1)]),
    )
    head_report.append(file_1)
    file_2 = ReportFile("jupiter.py")
    file_2.append(
        1,
        ReportLine.create(
            coverage=1, sessions=[LineSession(0, 1), LineSession(2, "1/2")]
        ),
    )
    file_2.append(
        40,
        ReportLine.create(coverage=1, sessions=[LineSession(5, 1), LineSession(2, 1)]),
    )
    base_report.append(file_2)
    mocker.patch(
        "services.bots.get_github_integration_token",
        return_value="github-integration-token",
    )
    return generate_sample_comparison(
        request.node.name,
        dbsession,
        ReadOnlyReport.create_from_report(base_report),
        ReadOnlyReport.create_from_report(head_report),
    )


@pytest.fixture
def mock_repo_provider(mock_repo_provider):
    compare_result = {
        "diff": {
            "files": {
                "file_1.go": {
                    "type": "modified",
                    "before": None,
                    "segments": [
                        {
                            "header": ["5", "8", "5", "9"],
                            "lines": [
                                " Overview",
                                " --------",
                                " ",
                                "-Main website: `Codecov <https://codecov.io/>`_.",
                                "-Main website: `Codecov <https://codecov.io/>`_.",
                                "+",
                                "+website: `Codecov <https://codecov.io/>`_.",
                                "+website: `Codecov <https://codecov.io/>`_.",
                                " ",
                                " .. code-block:: shell-session",
                                " ",
                            ],
                        },
                        {
                            "header": ["46", "12", "47", "19"],
                            "lines": [
                                " ",
                                " You may need to configure a ``.coveragerc`` file. Learn more `here <http://coverage.readthedocs.org/en/latest/config.html>`_. Start with this `generic .coveragerc <https://gist.github.com/codecov-io/bf15bde2c7db1a011b6e>`_ for example.",
                                " ",
                                "-We highly suggest adding `source` to your ``.coveragerc`` which solves a number of issues collecting coverage.",
                                "+We highly suggest adding ``source`` to your ``.coveragerc``, which solves a number of issues collecting coverage.",
                                " ",
                                " .. code-block:: ini",
                                " ",
                                "    [run]",
                                "    source=your_package_name",
                                "+   ",
                                "+If there are multiple sources, you instead should add ``include`` to your ``.coveragerc``",
                                "+",
                                "+.. code-block:: ini",
                                "+",
                                "+   [run]",
                                "+   include=your_package_name/*",
                                " ",
                                " unittests",
                                " ---------",
                            ],
                        },
                        {
                            "header": ["150", "5", "158", "4"],
                            "lines": [
                                " * Twitter: `@codecov <https://twitter.com/codecov>`_.",
                                " * Email: `hello@codecov.io <hello@codecov.io>`_.",
                                " ",
                                "-We are happy to help if you have any questions. Please contact email our Support at [support@codecov.io](mailto:support@codecov.io)",
                                "-",
                                "+We are happy to help if you have any questions. Please contact email our Support at `support@codecov.io <mailto:support@codecov.io>`_.",
                            ],
                        },
                    ],
                    "stats": {"added": 11, "removed": 4},
                }
            }
        },
        "commits": [
            {
                "commitid": "{comparison.base.commit[:7]}44fdd29fcc506317cc3ddeae1a723dd08",
                "message": "Update README.rst",
                "timestamp": "2018-07-09T23:51:16Z",
                "author": {
                    "id": 8398772,
                    "username": "jerrode",
                    "name": "Jerrod",
                    "email": "jerrod@fundersclub.com",
                },
            },
            {
                "commitid": "6ae5f1795a441884ed2847bb31154814ac01ef38",
                "message": "Update README.rst",
                "timestamp": "2018-04-26T08:35:58Z",
                "author": {
                    "id": 11602092,
                    "username": "TomPed",
                    "name": "Thomas Pedbereznak",
                    "email": "tom@tomped.com",
                },
            },
        ],
    }

    branch_result = {"name": "test", "sha": "aaaaaaa"}

    mock_repo_provider.get_compare.return_value = compare_result
    mock_repo_provider.post_comment.return_value = {}
    mock_repo_provider.edit_comment.return_value = {}
    mock_repo_provider.delete_comment.return_value = {}
    mock_repo_provider.get_branch.side_effect = TorngitClientGeneralError(
        404, None, "Branch not found"
    )
    return mock_repo_provider


class TestCommentNotifierHelpers(object):
    def test_sort_by_importance(self):
        modified_change = Change(
            path="modified.py",
            in_diff=True,
            totals=ReportTotals(
                files=0,
                lines=0,
                hits=-2,
                misses=1,
                partials=0,
                coverage=-23.333330000000004,
                branches=0,
                methods=0,
                messages=0,
                sessions=0,
                complexity=0,
                complexity_total=0,
                diff=0,
            ),
        )
        renamed_with_changes_change = Change(
            path="renamed_with_changes.py",
            in_diff=True,
            old_path="old_renamed_with_changes.py",
            totals=ReportTotals(
                files=0,
                lines=0,
                hits=-1,
                misses=1,
                partials=0,
                coverage=-20.0,
                branches=0,
                methods=0,
                messages=0,
                sessions=0,
                complexity=0,
                complexity_total=0,
                diff=0,
            ),
        )
        unrelated_change = Change(
            path="unrelated.py",
            in_diff=False,
            totals=ReportTotals(
                files=0,
                lines=0,
                hits=-3,
                misses=2,
                partials=0,
                coverage=-43.333330000000004,
                branches=0,
                methods=0,
                messages=0,
                sessions=0,
                complexity=0,
                complexity_total=0,
                diff=0,
            ),
        )
        added_change = Change(
            path="added.py", new=True, in_diff=None, old_path=None, totals=None
        )
        deleted_change = Change(path="deleted.py", deleted=True)
        changes = [
            modified_change,
            renamed_with_changes_change,
            unrelated_change,
            added_change,
            deleted_change,
        ]
        res = sort_by_importance(changes)
        expected_result = [
            unrelated_change,
            modified_change,
            renamed_with_changes_change,
            deleted_change,
            added_change,
        ]
        assert expected_result == res

    def test_format_number_to_str(self):
        assert "<0.1" == format_number_to_str(
            {"coverage": {"precision": 1}}, Decimal("0.001")
        )
        assert "10.0" == format_number_to_str(
            {"coverage": {"precision": 1}}, Decimal("10.001")
        )
        assert "10.1" == format_number_to_str(
            {"coverage": {"precision": 1, "round": "up"}}, Decimal("10.001")
        )

    def test_diff_to_string_case_1(self):
        case_1 = (
            "master",
            ReportTotals(10),
            "stable",
            ReportTotals(11),
            [
                "@@         Coverage Diff          @@",
                "##        master   stable   +/-   ##",
                "====================================",
                "====================================",
                "  Files       10       11    +1     ",
                "",
            ],
        )
        case = case_1
        base_title, base_totals, head_title, head_totals, expected_result = case
        diff = diff_to_string({}, base_title, base_totals, head_title, head_totals)
        assert diff == expected_result

    def test_diff_to_string_case_2(self):
        case_2 = (
            "master",
            ReportTotals(files=10, coverage="12.0", complexity="10.0"),
            "stable",
            ReportTotals(files=10, coverage="15.0", complexity="9.0"),
            [
                "@@             Coverage Diff              @@",
                "##             master   stable      +/-   ##",
                "============================================",
                "+ Coverage     12.00%   15.00%   +3.00%     ",
                "- Complexity   10.00%    9.00%   -1.00%     ",
                "============================================",
                "  Files            10       10              ",
                "",
            ],
        )
        case = case_2
        base_title, base_totals, head_title, head_totals, expected_result = case
        diff = diff_to_string({}, base_title, base_totals, head_title, head_totals)
        assert diff == expected_result

    def test_diff_to_string_case_3(self):
        case_3 = (
            "master",
            ReportTotals(files=100),
            "#1",
            ReportTotals(files=200, lines=2, hits=6, misses=7, partials=8, branches=3),
            [
                "@@          Coverage Diff          @@",
                "##           master    #1    +/-   ##",
                "=====================================",
                "=====================================",
                "  Files         100   200   +100     ",
                "  Lines           0     2     +2     ",
                "  Branches        0     3     +3     ",
                "=====================================",
                "+ Hits            0     6     +6     ",
                "- Misses          0     7     +7     ",
                "- Partials        0     8     +8     ",
            ],
        )
        case = case_3
        base_title, base_totals, head_title, head_totals, expected_result = case
        diff = diff_to_string({}, base_title, base_totals, head_title, head_totals)
        assert diff == expected_result

    def test_diff_to_string_case_4(self):
        case_4 = (
            "master",
            ReportTotals(files=10, coverage="12.0", complexity=10),
            "stable",
            ReportTotals(files=10, coverage="15.0", complexity=9),
            [
                "@@             Coverage Diff              @@",
                "##             master   stable      +/-   ##",
                "============================================",
                "+ Coverage     12.00%   15.00%   +3.00%     ",
                "+ Complexity       10        9       -1     ",
                "============================================",
                "  Files            10       10              ",
                "",
            ],
        )
        case = case_4
        base_title, base_totals, head_title, head_totals, expected_result = case
        diff = diff_to_string({}, base_title, base_totals, head_title, head_totals)
        assert diff == expected_result

    def test_diff_to_string_case_different_types(self):
        case_1 = (
            "master",
            ReportTotals(10, coverage="54.43"),
            "stable",
            ReportTotals(11, coverage=0),
            [
                "@@             Coverage Diff             @@",
                "##           master   stable       +/-   ##",
                "===========================================",
                "- Coverage   54.43%        0   -54.43%     ",
                "===========================================",
                "  Files          10       11        +1     ",
                "",
            ],
        )
        case = case_1
        base_title, base_totals, head_title, head_totals, expected_result = case
        diff = diff_to_string({}, base_title, base_totals, head_title, head_totals)
        assert diff == expected_result

    @pytest.mark.asyncio
    async def test__possibly_write_gh_app_login_announcement_should_add_announcement(
        self, dbsession, mocker
    ):
        repository = RepositoryFactory.create(
            owner__service="github", owner__integration_id=None
        )  # Not using integration
        dbsession.add(repository)
        dbsession.flush()
        mocker.patch(
            "services.notification.notifiers.mixins.message.is_enterprise",
            return_value=False,
        )
        mock_write = mocker.MagicMock()

        notifier = CommentNotifier(
            repository=repository,
            title="some_title",
            notifier_yaml_settings=False,
            notifier_site_settings=None,
            current_yaml={},
        )
        fake_comparison = mocker.MagicMock()
        fake_comparison.head.commit.repository = repository
        await notifier._possibly_write_gh_app_login_announcement(
            fake_comparison, mock_write
        )
        mock_write.assert_any_call(
            ":exclamation: Your organization needs to install the [Codecov GitHub app](https://github.com/apps/codecov/installations/select_target) to enable full functionality.",
        )
        assert mock_write.call_count == 2

    @pytest.mark.asyncio
    async def test__possibly_write_gh_app_login_announcement_already_using_integration(
        self, dbsession, mocker
    ):
        repository = RepositoryFactory.create(
            owner__service="github", owner__integration_id="10000"
        )  # Using integration
        dbsession.add(repository)
        dbsession.flush()
        mocker.patch(
            "services.notification.notifiers.mixins.message.is_enterprise",
            return_value=False,
        )
        mock_write = mocker.MagicMock()

        notifier = CommentNotifier(
            repository=repository,
            title="some_title",
            notifier_yaml_settings=False,
            notifier_site_settings=None,
            current_yaml={},
        )
        fake_comparison = mocker.MagicMock()
        fake_comparison.head.commit.repository = repository
        await notifier._possibly_write_gh_app_login_announcement(
            fake_comparison, mock_write
        )
        assert mock_write.call_count == 0

    @pytest.mark.asyncio
    async def test__possibly_write_gh_app_login_announcement_enterprise(
        self, dbsession, mocker
    ):
        repository = RepositoryFactory.create(
            owner__service="github", owner__integration_id=None
        )  # Not using integration
        dbsession.add(repository)
        dbsession.flush()
        mocker.patch(
            "services.notification.notifiers.mixins.message.is_enterprise",
            return_value=True,
        )  # Enterprise

        mock_write = mocker.MagicMock()

        notifier = CommentNotifier(
            repository=repository,
            title="some_title",
            notifier_yaml_settings=False,
            notifier_site_settings=None,
            current_yaml={},
        )
        fake_comparison = mocker.MagicMock()
        fake_comparison.head.commit.repository = repository
        await notifier._possibly_write_gh_app_login_announcement(
            fake_comparison, mock_write
        )
        assert mock_write.call_count == 0


@pytest.mark.usefixtures("is_not_first_pull")
class TestCommentNotifier(object):
    @pytest.mark.asyncio
    async def test_is_enabled_settings_individual_settings_false(self, dbsession):
        repository = RepositoryFactory.create()
        dbsession.add(repository)
        dbsession.flush()
        notifier = CommentNotifier(
            repository=repository,
            title="some_title",
            notifier_yaml_settings=False,
            notifier_site_settings=None,
            current_yaml={},
        )
        assert not notifier.is_enabled()

    @pytest.mark.asyncio
    async def test_is_enabled_settings_individual_settings_none(self, dbsession):
        repository = RepositoryFactory.create()
        dbsession.add(repository)
        dbsession.flush()
        notifier = CommentNotifier(
            repository=repository,
            title="some_title",
            notifier_yaml_settings=None,
            notifier_site_settings=None,
            current_yaml={},
        )
        assert not notifier.is_enabled()

    @pytest.mark.asyncio
    async def test_is_enabled_settings_individual_settings_true(self, dbsession):
        repository = RepositoryFactory.create()
        dbsession.add(repository)
        dbsession.flush()
        notifier = CommentNotifier(
            repository=repository,
            title="some_title",
            notifier_yaml_settings=True,
            notifier_site_settings=None,
            current_yaml={},
        )
        assert not notifier.is_enabled()

    @pytest.mark.asyncio
    async def test_is_enabled_settings_individual_settings_dict(self, dbsession):
        repository = RepositoryFactory.create()
        dbsession.add(repository)
        dbsession.flush()
        notifier = CommentNotifier(
            repository=repository,
            title="some_title",
            notifier_yaml_settings={"layout": "reach, diff, flags, files, footer"},
            notifier_site_settings=None,
            current_yaml={},
        )
        assert notifier.is_enabled()

    @pytest.mark.asyncio
    async def test_create_message_files_section(
        self,
        dbsession,
        mock_configuration,
        mock_repo_provider,
        sample_comparison,
        mocker,
    ):
        comparison = sample_comparison
        mocker.patch.object(comparison, "get_behind_by", return_value=0)
        mocker.patch.object(
            comparison,
            "get_diff",
            return_value={
                "files": {
                    "file_1.go": {
                        "type": "modified",
                        "before": None,
                        "segments": [
                            {
                                "header": ["105", "8", "105", "9"],
                                "lines": [
                                    " Overview",
                                    " --------",
                                    " ",
                                    "-Main website: `Codecov <https://codecov.io/>`_.",
                                    "-Main website: `Codecov <https://codecov.io/>`_.",
                                    "+",
                                    "+website: `Codecov <https://codecov.io/>`_.",
                                    "+website: `Codecov <https://codecov.io/>`_.",
                                    " ",
                                    " .. code-block:: shell-session",
                                    " ",
                                ],
                            },
                            {
                                "header": ["1046", "12", "1047", "19"],
                                "lines": [
                                    " ",
                                    " You may need to configure a ``.coveragerc`` file. Learn more",
                                    " ",
                                    "-We highly suggest adding `source` to your ``.coveragerc``",
                                    "+We highly suggest adding ``source`` to your ``.coveragerc`",
                                    " ",
                                    " .. code-block:: ini",
                                    " ",
                                    "    [run]",
                                    "    source=your_package_name",
                                    "+   ",
                                    "+If there are multiple sources, you instead should add ``include",
                                    "+",
                                    "+.. code-block:: ini",
                                    "+",
                                    "+   [run]",
                                    "+   include=your_package_name/*",
                                    " ",
                                    " unittests",
                                    " ---------",
                                ],
                            },
                            {
                                "header": ["10150", "5", "10158", "4"],
                                "lines": [
                                    " * Twitter: `@codecov <https://twitter.com/codecov>`_.",
                                    " * Email: `hello@codecov.io <hello@codecov.io>`_.",
                                    " ",
                                    "-We are happy to help if you have any questions. ",
                                    "-",
                                    "+We are happy to help if you have any questions. .",
                                ],
                            },
                        ],
                        "stats": {"added": 11, "removed": 4},
                    },
                    "file_2.py": {
                        "type": "modified",
                        "before": None,
                        "segments": [
                            {
                                "header": ["10", "8", "10", "9"],
                                "lines": [
                                    " Overview",
                                    " --------",
                                    " ",
                                    "-Main website: `Codecov <https://codecov.io/>`_.",
                                    "-Main website: `Codecov <https://codecov.io/>`_.",
                                    "+",
                                    "+website: `Codecov <https://codecov.io/>`_.",
                                    "+website: `Codecov <https://codecov.io/>`_.",
                                    " ",
                                    " .. code-block:: shell-session",
                                    " ",
                                ],
                            },
                            {
                                "header": ["50", "12", "51", "19"],
                                "lines": [
                                    " ",
                                    " You may need to configure a ``.coveragerc`` file. Learn more `here <http://coverage.readthedocs.org/en/latest/config.html>`_. Start with this `generic .coveragerc <https://gist.github.com/codecov-io/bf15bde2c7db1a011b6e>`_ for example.",
                                    " ",
                                    "-We highly suggest adding `source` to your ``.coveragerc`` which solves a number of issues collecting coverage.",
                                    "+We highly suggest adding ``source`` to your ``.coveragerc``, which solves a number of issues collecting coverage.",
                                    " ",
                                    " .. code-block:: ini",
                                    " ",
                                    "    [run]",
                                    "    source=your_package_name",
                                    "+   ",
                                    "+If there are multiple sources, you instead should add ``include`` to your ``.coveragerc``",
                                    "+",
                                    "+.. code-block:: ini",
                                    "+",
                                    "+   [run]",
                                    "+   include=your_package_name/*",
                                    " ",
                                    " unittests",
                                    " ---------",
                                ],
                            },
                        ],
                        "stats": {"added": 11, "removed": 4},
                    },
                }
            },
        )
        pull_dict = {"base": {"branch": "master"}}
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={"layout": "files"},
            notifier_site_settings=True,
            current_yaml={},
        )
        pull = comparison.pull
        repository = sample_comparison.head.commit.repository
        expected_result = [
            f"## [Codecov](https://app.codecov.io/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=h1) Report",
            f"> Merging [#{pull.pullid}](https://app.codecov.io/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=desc) ({sample_comparison.head.commit.commitid[:7]}) into [master](https://app.codecov.io/gh/{repository.slug}/commit/{sample_comparison.base.commit.commitid}?el=desc) ({sample_comparison.base.commit.commitid[:7]}) will **increase** coverage by `10.00%`.",
            f"> The diff coverage is `n/a`.",
            f"",
            f"| [Files](https://app.codecov.io/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree) | Coverage Δ | Complexity Δ | |",
            f"|---|---|---|---|",
            f"| [file\\_1.go](https://app.codecov.io/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree#diff-ZmlsZV8xLmdv) | `62.50% <ø> (+12.50%)` | `10.00 <0.00> (-1.00)` | :arrow_up: |",
            f"| [file\\_2.py](https://app.codecov.io/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree#diff-ZmlsZV8yLnB5) | `50.00% <ø> (ø)` | `0.00 <0.00> (ø)` | |",
            f"",
        ]
        res = await notifier.create_message(comparison, pull_dict, {"layout": "files"})
        print(res)
        assert expected_result == res

    @pytest.mark.asyncio
    async def test_create_message_files_section_with_critical_files(
        self,
        dbsession,
        mock_configuration,
        mock_repo_provider,
        sample_comparison,
        mocker,
    ):
        comparison = sample_comparison
        mocker.patch.object(
            comparison,
            "get_diff",
            return_value={
                "files": {
                    "file_1.go": {
                        "type": "modified",
                        "before": None,
                        "segments": [
                            {
                                "header": ["105", "8", "105", "9"],
                                "lines": [
                                    " Overview",
                                    " --------",
                                    " ",
                                    "-Main website: `Codecov <https://codecov.io/>`_.",
                                    "-Main website: `Codecov <https://codecov.io/>`_.",
                                    "+",
                                    "+website: `Codecov <https://codecov.io/>`_.",
                                    "+website: `Codecov <https://codecov.io/>`_.",
                                    " ",
                                    " .. code-block:: shell-session",
                                    " ",
                                ],
                            },
                            {
                                "header": ["1046", "12", "1047", "19"],
                                "lines": [
                                    " ",
                                    " You may need to configure a ``.coveragerc`` file. Learn more",
                                    " ",
                                    "-We highly suggest adding `source` to your ``.coveragerc``",
                                    "+We highly suggest adding ``source`` to your ``.coveragerc`",
                                    " ",
                                    " .. code-block:: ini",
                                    " ",
                                    "    [run]",
                                    "    source=your_package_name",
                                    "+   ",
                                    "+If there are multiple sources, you instead should add ``include",
                                    "+",
                                    "+.. code-block:: ini",
                                    "+",
                                    "+   [run]",
                                    "+   include=your_package_name/*",
                                    " ",
                                    " unittests",
                                    " ---------",
                                ],
                            },
                            {
                                "header": ["10150", "5", "10158", "4"],
                                "lines": [
                                    " * Twitter: `@codecov <https://twitter.com/codecov>`_.",
                                    " * Email: `hello@codecov.io <hello@codecov.io>`_.",
                                    " ",
                                    "-We are happy to help if you have any questions. ",
                                    "-",
                                    "+We are happy to help if you have any questions. .",
                                ],
                            },
                        ],
                        "stats": {"added": 11, "removed": 4},
                    },
                    "file_2.py": {
                        "type": "modified",
                        "before": None,
                        "segments": [
                            {
                                "header": ["10", "8", "10", "9"],
                                "lines": [
                                    " Overview",
                                    " --------",
                                    " ",
                                    "-Main website: `Codecov <https://codecov.io/>`_.",
                                    "-Main website: `Codecov <https://codecov.io/>`_.",
                                    "+",
                                    "+website: `Codecov <https://codecov.io/>`_.",
                                    "+website: `Codecov <https://codecov.io/>`_.",
                                    " ",
                                    " .. code-block:: shell-session",
                                    " ",
                                ],
                            },
                            {
                                "header": ["50", "12", "51", "19"],
                                "lines": [
                                    " ",
                                    " You may need to configure a ``.coveragerc`` file. Learn more `here <http://coverage.readthedocs.org/en/latest/config.html>`_. Start with this `generic .coveragerc <https://gist.github.com/codecov-io/bf15bde2c7db1a011b6e>`_ for example.",
                                    " ",
                                    "-We highly suggest adding `source` to your ``.coveragerc`` which solves a number of issues collecting coverage.",
                                    "+We highly suggest adding ``source`` to your ``.coveragerc``, which solves a number of issues collecting coverage.",
                                    " ",
                                    " .. code-block:: ini",
                                    " ",
                                    "    [run]",
                                    "    source=your_package_name",
                                    "+   ",
                                    "+If there are multiple sources, you instead should add ``include`` to your ``.coveragerc``",
                                    "+",
                                    "+.. code-block:: ini",
                                    "+",
                                    "+   [run]",
                                    "+   include=your_package_name/*",
                                    " ",
                                    " unittests",
                                    " ---------",
                                ],
                            },
                        ],
                        "stats": {"added": 11, "removed": 4},
                    },
                }
            },
        )
        mocked_search_files_for_critical_changes = mocker.patch.object(
            CriticalPathOverlay,
            "search_files_for_critical_changes",
            return_value=["file_2.py"],
        )
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "files,betaprofiling",
                "show_critical_paths": True,
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        pull = comparison.pull
        repository = sample_comparison.head.commit.repository
        expected_result = [
            f"## [Codecov](https://app.codecov.io/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=h1) Report",
            f"> Merging [#{pull.pullid}](https://app.codecov.io/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=desc) ({sample_comparison.head.commit.commitid[:7]}) into [master](https://app.codecov.io/gh/{repository.slug}/commit/{sample_comparison.base.commit.commitid}?el=desc) ({sample_comparison.base.commit.commitid[:7]}) will **increase** coverage by `10.00%`.",
            "> The diff coverage is `n/a`.",
            "",
            "Changes have been made to critical files, which contain lines commonly executed in production. [Learn more](https://docs.codecov.com/docs/impact-analysis)",
            "",
            f"| [Files](https://app.codecov.io/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree) | Coverage Δ | Complexity Δ | |",
            f"|---|---|---|---|",
            f"| [file\\_1.go](https://app.codecov.io/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree#diff-ZmlsZV8xLmdv) | `62.50% <ø> (+12.50%)` | `10.00 <0.00> (-1.00)` | :arrow_up: |",
            f"| [file\\_2.py](https://app.codecov.io/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree#diff-ZmlsZV8yLnB5) **Critical** | `50.00% <ø> (ø)` | `0.00 <0.00> (ø)` | |",
            f"",
            "",
        ]
        res = await notifier.build_message(comparison)
        assert expected_result == res
        mocked_search_files_for_critical_changes.assert_called_with(
            {"file_2.py", "file_1.go"}
        )
        assert mocked_search_files_for_critical_changes.call_count == 2

    @pytest.mark.asyncio
    async def test_build_message(
        self, dbsession, mock_configuration, mock_repo_provider, sample_comparison
    ):
        mock_configuration.params["setup"]["codecov_dashboard_url"] = "test.example.br"
        comparison = sample_comparison
        pull = comparison.pull
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={"layout": "reach, diff, flags, files, footer"},
            notifier_site_settings=True,
            current_yaml={},
        )
        repository = sample_comparison.head.commit.repository
        result = await notifier.build_message(comparison)
        expected_result = [
            f"## [Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=h1) Report",
            f"> Merging [#{pull.pullid}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=desc) ({comparison.head.commit.commitid[:7]}) into [master](test.example.br/gh/{repository.slug}/commit/{sample_comparison.base.commit.commitid}?el=desc) ({sample_comparison.base.commit.commitid[:7]}) will **increase** coverage by `10.00%`.",
            f"> The diff coverage is `66.67%`.",
            f"",
            f"[![Impacted file tree graph](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/graphs/tree.svg?width=650&height=150&src=pr&token={repository.image_token})](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree)",
            f"",
            f"```diff",
            f"@@              Coverage Diff              @@",
            f"##             master      #{pull.pullid}       +/-   ##",
            f"=============================================",
            f"+ Coverage     50.00%   60.00%   +10.00%     ",
            f"+ Complexity       11       10        -1     ",
            f"=============================================",
            f"  Files             2        2               ",
            f"  Lines             6       10        +4     ",
            f"  Branches          0        1        +1     ",
            f"=============================================",
            f"+ Hits              3        6        +3     ",
            f"  Misses            3        3               ",
            f"- Partials          0        1        +1     ",
            f"```",
            f"",
            f"| [Flag](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flags) | Coverage Δ | Complexity Δ | |",
            f"|---|---|---|---|",
            f"| [integration](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `?` | `?` | |",
            f"| [unit](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `100.00% <100.00%> (?)` | `0.00 <0.00> (?)` | |",
            f"",
            f"Flags with carried forward coverage won't be shown. [Click here](https://docs.codecov.io/docs/carryforward-flags#carryforward-flags-in-the-pull-request-comment) to find out more.",
            f"",
            f"| [Files](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree) | Coverage Δ | Complexity Δ | |",
            f"|---|---|---|---|",
            f"| [file\\_1.go](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree#diff-ZmlsZV8xLmdv) | `62.50% <66.67%> (+12.50%)` | `10.00 <0.00> (-1.00)` | :arrow_up: |",
            f"",
            f"... and [1 file with indirect coverage changes](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/indirect-changes?src=pr&el=tree-more)",
            f"",
            f"------",
            f"",
            f"[Continue to review full report in "
            f"Codecov by Sentry](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=continue).",
            f"> **Legend** - [Click here to learn "
            f"more](https://docs.codecov.io/docs/codecov-delta)",
            f"> `Δ = absolute <relative> (impact)`, `ø = not affected`, `? = missing data`",
            f"> Powered by "
            f"[Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=footer). "
            f"Last update "
            f"[{sample_comparison.base.commit.commitid[:7]}...{sample_comparison.head.commit.commitid[:7]}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=lastupdated). "
            f"Read the [comment docs](https://docs.codecov.io/docs/pull-request-comments).",
            f"",
        ]
        for exp, res in zip(expected_result, result):
            assert exp == res
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_build_message_flags_empty_coverage(
        self,
        dbsession,
        mock_configuration,
        mock_repo_provider,
        sample_comparison_bunch_empty_flags,
    ):
        mock_configuration.params["setup"]["codecov_dashboard_url"] = "test.example.br"
        comparison = sample_comparison_bunch_empty_flags
        pull = comparison.pull
        notifier = CommentNotifier(
            repository=comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={"layout": "flags"},
            notifier_site_settings=True,
            current_yaml={},
        )
        repository = comparison.head.commit.repository
        result = await notifier.build_message(comparison)
        expected_result = [
            f"## [Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=h1) Report",
            f"> Merging [#{pull.pullid}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=desc) ({comparison.head.commit.commitid[:7]}) into [master](test.example.br/gh/{repository.slug}/commit/{comparison.base.commit.commitid}?el=desc) ({comparison.base.commit.commitid[:7]}) will **not change** coverage.",
            f"> The diff coverage is `n/a`.",
            f"",
            f"| [Flag](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flags) | Coverage Δ | |",
            "|---|---|---|",
            f"| [eighth](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `?` | |",
            f"| [fifth](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `∅ <ø> (?)` | |",
            f"| [first](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `100.00% <ø> (ø)` | |",
            f"| [fourth](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `∅ <ø> (∅)` | |",
            f"| [second](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `50.00% <ø> (∅)` | |",
            f"| [seventh](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `?` | |",
            f"| [sixth](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `100.00% <ø> (?)` | |",
            f"| [third](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `∅ <ø> (∅)` | |",
            "",
            "Flags with carried forward coverage won't be shown. [Click here](https://docs.codecov.io/docs/carryforward-flags#carryforward-flags-in-the-pull-request-comment) to find out more.",
            "",
        ]
        li = 0
        print("\n".join(result))
        for exp, res in zip(expected_result, result):
            li += 1
            print(li)
            assert exp == res
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_build_message_more_sections(
        self, dbsession, mock_configuration, mock_repo_provider, sample_comparison
    ):
        mock_configuration.params["setup"]["codecov_dashboard_url"] = "test.example.br"
        comparison = sample_comparison
        pull = comparison.pull
        all_sections = [
            "reach, diff, flags, files, footer",
            "changes",
            "file",
            "header",
            "suggestions",
            "sunburst",
            "uncovered",
            "random_section",
        ]
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={"layout": ",".join(all_sections)},
            notifier_site_settings=True,
            current_yaml={},
        )
        repository = sample_comparison.head.commit.repository
        result = await notifier.build_message(comparison)
        expected_result = [
            f"## [Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=h1) Report",
            f"> Merging [#{pull.pullid}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=desc) ({comparison.head.commit.commitid[:7]}) into [master](test.example.br/gh/{repository.slug}/commit/{sample_comparison.base.commit.commitid}?el=desc) ({sample_comparison.base.commit.commitid[:7]}) will **increase** coverage by `10.00%`.",
            f"> The diff coverage is `66.67%`.",
            f"",
            f"[![Impacted file tree graph](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/graphs/tree.svg?width=650&height=150&src=pr&token={repository.image_token})](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree)",
            f"",
            f"```diff",
            f"@@              Coverage Diff              @@",
            f"##             master      #{pull.pullid}       +/-   ##",
            f"=============================================",
            f"+ Coverage     50.00%   60.00%   +10.00%     ",
            f"+ Complexity       11       10        -1     ",
            f"=============================================",
            f"  Files             2        2               ",
            f"  Lines             6       10        +4     ",
            f"  Branches          0        1        +1     ",
            f"=============================================",
            f"+ Hits              3        6        +3     ",
            f"  Misses            3        3               ",
            f"- Partials          0        1        +1     ",
            f"```",
            f"",
            f"| [Flag](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flags) | Coverage Δ | Complexity Δ | |",
            f"|---|---|---|---|",
            f"| [integration](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `?` | `?` | |",
            f"| [unit](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `100.00% <100.00%> (?)` | `0.00 <0.00> (?)` | |",
            f"",
            f"Flags with carried forward coverage won't be shown. [Click here](https://docs.codecov.io/docs/carryforward-flags#carryforward-flags-in-the-pull-request-comment) to find out more.",
            f"",
            f"| [Files](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree) | Coverage Δ | Complexity Δ | |",
            f"|---|---|---|---|",
            f"| [file\\_1.go](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree#diff-ZmlsZV8xLmdv) | `62.50% <66.67%> (+12.50%)` | `10.00 <0.00> (-1.00)` | :arrow_up: |",
            f"",
            f"... and [1 file with indirect coverage changes](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/indirect-changes?src=pr&el=tree-more)",
            f"",
            f"------",
            f"",
            f"[Continue to review full report in "
            f"Codecov by Sentry](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=continue).",
            f"> **Legend** - [Click here to learn "
            f"more](https://docs.codecov.io/docs/codecov-delta)",
            f"> `Δ = absolute <relative> (impact)`, `ø = not affected`, `? = missing data`",
            f"> Powered by "
            f"[Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=footer). "
            f"Last update "
            f"[{sample_comparison.base.commit.commitid[:7]}...{sample_comparison.head.commit.commitid[:7]}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=lastupdated). "
            f"Read the [comment docs](https://docs.codecov.io/docs/pull-request-comments).",
            f"",
            f"",
            f"",
            f"",
            f"",
            f"",
            f"",
        ]
        for exp, res in zip(expected_result, result):
            assert exp == res
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_build_upgrade_message(
        self,
        request,
        dbsession,
        mocker,
        mock_configuration,
        with_sql_functions,
        sample_comparison,
    ):
        mock_configuration.params["setup"]["codecov_dashboard_url"] = "test.example.br"
        mocker.patch("services.license.is_enterprise", return_value=False)
        comparison = sample_comparison
        pull = comparison.enriched_pull.database_pull
        repository = sample_comparison.head.commit.repository
        notifier = CommentNotifier(
            repository=repository,
            title="title",
            notifier_yaml_settings={"layout": "reach, diff, flags, files, footer"},
            notifier_site_settings=True,
            current_yaml={},
            decoration_type=Decoration.upgrade,
        )
        result = await notifier.build_message(comparison)
        provider_pull = comparison.enriched_pull.provider_pull
        expected_result = [
            f"The author of this PR, {provider_pull['author']['username']}, is not an activated member of this organization on Codecov.",
            f"Please [activate this user on Codecov](test.example.br/members/gh/{pull.repository.owner.username}) to display this PR comment.",
            f"Coverage data is still being uploaded to Codecov.io for purposes of overall coverage calculations.",
            f"Please don't hesitate to email us at support@codecov.io with any questions.",
        ]
        li = 0
        for exp, res in zip(expected_result, result):
            li += 1
            assert exp == res
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_build_limited_upload_message(
        self,
        request,
        dbsession,
        mocker,
        mock_configuration,
        with_sql_functions,
        sample_comparison,
    ):
        mock_configuration.params["setup"] = {
            "codecov_url": "test.example.br",
            "codecov_dashboard_url": "test.example.br",
        }
        comparison = sample_comparison
        pull = comparison.enriched_pull.database_pull
        repository = sample_comparison.head.commit.repository
        notifier = CommentNotifier(
            repository=repository,
            title="title",
            notifier_yaml_settings={"layout": "reach, diff, flags, files, footer"},
            notifier_site_settings=True,
            current_yaml={},
            decoration_type=Decoration.upload_limit,
        )
        result = await notifier.build_message(comparison)
        expected_result = [
            f"## [Codecov](test.example.br/plan/gh/{pull.repository.owner.username}) upload limit reached :warning:",
            f"This org is currently on the free Basic Plan; which includes 250 free private repo uploads each rolling month.\
                 This limit has been reached and additional reports cannot be generated. For unlimited uploads,\
                      upgrade to our [pro plan](test.example.br/plan/gh/{pull.repository.owner.username}).",
            f"",
            f"**Do you have questions or need help?** Connect with our sales team today at ` sales@codecov.io `",
        ]
        li = 0
        for exp, res in zip(expected_result, result):
            li += 1
            assert exp == res
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_build_passing_empty_upload(
        self,
        request,
        dbsession,
        mocker,
        mock_configuration,
        with_sql_functions,
        sample_comparison,
    ):
        mock_configuration.params["setup"] = {
            "codecov_url": "test.example.br",
            "codecov_dashboard_url": "test.example.br",
        }
        comparison = sample_comparison
        pull = comparison.enriched_pull.database_pull
        repository = sample_comparison.head.commit.repository
        notifier = CommentNotifier(
            repository=repository,
            title="title",
            notifier_yaml_settings={"layout": "reach, diff, flags, files, footer"},
            notifier_site_settings=True,
            current_yaml={},
            decoration_type=Decoration.passing_empty_upload,
        )
        result = await notifier.build_message(comparison)
        expected_result = [
            "## Codecov Report",
            ":heavy_check_mark: **No coverage data to report**, because files changed do not require tests or are set to [ignore](https://docs.codecov.com/docs/ignoring-paths#:~:text=You%20can%20use%20the%20top,will%20be%20skipped%20during%20processing.) ",
        ]
        for exp, res in zip(expected_result, result):
            assert exp == res
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_build_failing_empty_upload(
        self,
        request,
        dbsession,
        mocker,
        mock_configuration,
        with_sql_functions,
        sample_comparison,
    ):
        mock_configuration.params["setup"] = {
            "codecov_url": "test.example.br",
            "codecov_dashboard_url": "test.example.br",
        }
        comparison = sample_comparison
        pull = comparison.enriched_pull.database_pull
        repository = sample_comparison.head.commit.repository
        notifier = CommentNotifier(
            repository=repository,
            title="title",
            notifier_yaml_settings={"layout": "reach, diff, flags, files, footer"},
            notifier_site_settings=True,
            current_yaml={},
            decoration_type=Decoration.failing_empty_upload,
        )
        result = await notifier.build_message(comparison)
        expected_result = [
            "## Codecov Report",
            "This is an empty upload",
            "Files changed in this PR are testable or aren't ignored by Codecov, please run your tests and upload coverage. If you wish to ignore these files, please visit our [ignoring paths docs](https://docs.codecov.com/docs/ignoring-paths).",
        ]
        for exp, res in zip(expected_result, result):
            assert exp == res
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_processing_upload(
        self,
        request,
        dbsession,
        mocker,
        mock_configuration,
        with_sql_functions,
        sample_comparison,
    ):
        mock_configuration.params["setup"] = {
            "codecov_url": "test.example.br",
            "codecov_dashboard_url": "test.example.br",
        }
        comparison = sample_comparison
        pull = comparison.enriched_pull.database_pull
        repository = sample_comparison.head.commit.repository
        notifier = CommentNotifier(
            repository=repository,
            title="title",
            notifier_yaml_settings={"layout": "reach, diff, flags, files, footer"},
            notifier_site_settings=True,
            current_yaml={},
            decoration_type=Decoration.processing_upload,
        )
        result = await notifier.build_message(comparison)
        expected_result = [
            "We're currently processing your upload.  This comment will be updated when the results are available.",
        ]
        for exp, res in zip(expected_result, result):
            assert exp == res
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_build_upgrade_message_enterprise(
        self,
        request,
        dbsession,
        mocker,
        mock_configuration,
        with_sql_functions,
        sample_comparison,
    ):
        mocker.patch("services.license.is_enterprise", return_value=True)

        encrypted_license = "wxWEJyYgIcFpi6nBSyKQZQeaQ9Eqpo3SXyUomAqQOzOFjdYB3A8fFM1rm+kOt2ehy9w95AzrQqrqfxi9HJIb2zLOMOB9tSy52OykVCzFtKPBNsXU/y5pQKOfV7iI3w9CHFh3tDwSwgjg8UsMXwQPOhrpvl2GdHpwEhFdaM2O3vY7iElFgZfk5D9E7qEnp+WysQwHKxDeKLI7jWCnBCBJLDjBJRSz0H7AfU55RQDqtTrnR+rsLDHOzJ80/VxwVYhb"
        mock_configuration.params["setup"]["enterprise_license"] = encrypted_license
        mock_configuration.params["setup"][
            "codecov_dashboard_url"
        ] = "https://codecov.mysite.com"

        comparison = sample_comparison
        pull = comparison.enriched_pull.database_pull
        repository = sample_comparison.head.commit.repository
        notifier = CommentNotifier(
            repository=repository,
            title="title",
            notifier_yaml_settings={"layout": "reach, diff, flags, files, footer"},
            notifier_site_settings=True,
            current_yaml={},
            decoration_type=Decoration.upgrade,
        )
        result = await notifier.build_message(comparison)
        provider_pull = comparison.enriched_pull.provider_pull
        expected_result = [
            f"The author of this PR, {provider_pull['author']['username']}, is not activated in your Codecov Self-Hosted installation.",
            f"Please [activate this user](https://codecov.mysite.com/internal/users) to display this PR comment.",
            f"Coverage data is still being uploaded to Codecov Self-Hosted for the purposes of overall coverage calculations.",
            f"Please contact your Codecov On-Premises installation administrator with any questions.",
        ]
        li = 0
        for exp, res in zip(expected_result, result):
            li += 1
            assert exp == res
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_build_message_hide_complexity(
        self, dbsession, mock_configuration, mock_repo_provider, sample_comparison
    ):
        mock_configuration.params["setup"]["codecov_dashboard_url"] = "test.example.br"
        comparison = sample_comparison
        pull = comparison.pull
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={"layout": "reach, diff, flags, files, footer"},
            notifier_site_settings=True,
            current_yaml={"codecov": {"ui": {"hide_complexity": True}}},
        )
        repository = sample_comparison.head.commit.repository
        result = await notifier.build_message(comparison)
        expected_result = [
            f"## [Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=h1) Report",
            f"> Merging [#{pull.pullid}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=desc) ({comparison.head.commit.commitid[:7]}) into [master](test.example.br/gh/{repository.slug}/commit/{sample_comparison.base.commit.commitid}?el=desc) ({sample_comparison.base.commit.commitid[:7]}) will **increase** coverage by `10.00%`.",
            f"> The diff coverage is `66.67%`.",
            f"",
            f"[![Impacted file tree graph](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/graphs/tree.svg?width=650&height=150&src=pr&token={repository.image_token})](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree)",
            f"",
            f"```diff",
            f"@@              Coverage Diff              @@",
            f"##             master      #{pull.pullid}       +/-   ##",
            f"=============================================",
            f"+ Coverage     50.00%   60.00%   +10.00%     ",
            f"+ Complexity       11       10        -1     ",
            f"=============================================",
            f"  Files             2        2               ",
            f"  Lines             6       10        +4     ",
            f"  Branches          0        1        +1     ",
            f"=============================================",
            f"+ Hits              3        6        +3     ",
            f"  Misses            3        3               ",
            f"- Partials          0        1        +1     ",
            f"```",
            f"",
            f"| [Flag](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flags) | Coverage Δ | |",
            f"|---|---|---|",
            f"| [integration](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `?` | |",
            f"| [unit](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `100.00% <100.00%> (?)` | |",
            f"",
            f"Flags with carried forward coverage won't be shown. [Click here](https://docs.codecov.io/docs/carryforward-flags#carryforward-flags-in-the-pull-request-comment) to find out more.",
            f"",
            f"| [Files](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree) | Coverage Δ | |",
            f"|---|---|---|",
            f"| [file\\_1.go](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree#diff-ZmlsZV8xLmdv) | `62.50% <66.67%> (+12.50%)` | :arrow_up: |",
            f"",
            f"... and [1 file with indirect coverage changes](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/indirect-changes?src=pr&el=tree-more)",
            f"",
            f"------",
            f"",
            f"[Continue to review full report in "
            f"Codecov by Sentry](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=continue).",
            f"> **Legend** - [Click here to learn "
            f"more](https://docs.codecov.io/docs/codecov-delta)",
            f"> `Δ = absolute <relative> (impact)`, `ø = not affected`, `? = missing data`",
            f"> Powered by "
            f"[Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=footer). "
            f"Last update "
            f"[{sample_comparison.base.commit.commitid[:7]}...{sample_comparison.head.commit.commitid[:7]}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=lastupdated). "
            f"Read the [comment docs](https://docs.codecov.io/docs/pull-request-comments).",
            f"",
        ]
        for exp, res in zip(expected_result, result):
            assert exp == res
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_build_message_no_base_report(
        self,
        dbsession,
        mock_configuration,
        mock_repo_provider,
        sample_comparison_without_base_report,
    ):
        mock_configuration.params["setup"]["codecov_dashboard_url"] = "test.example.br"
        comparison = sample_comparison_without_base_report
        pull = comparison.pull
        notifier = CommentNotifier(
            repository=comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={"layout": "reach, diff, flags, files, footer"},
            notifier_site_settings=True,
            current_yaml={},
        )
        repository = comparison.head.commit.repository
        result = await notifier.build_message(comparison)
        expected_result = [
            f"## [Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=h1) Report",
            f"> :exclamation: No coverage uploaded for pull request base (`master@{comparison.base.commit.commitid[:7]}`). [Click here to learn what that means](https://docs.codecov.io/docs/error-reference#section-missing-base-commit).",
            f"> The diff coverage is `66.67%`.",
            f"",
            f"[![Impacted file tree graph](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/graphs/tree.svg?width=650&height=150&src=pr&token={repository.image_token})](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree)",
            f"",
            f"```diff",
            f"@@            Coverage Diff            @@",
            f"##             master      #{pull.pullid}   +/-   ##",
            f"=========================================",
            f"  Coverage          ?   60.00%           ",
            f"  Complexity        ?       10           ",
            f"=========================================",
            f"  Files             ?        2           ",
            f"  Lines             ?       10           ",
            f"  Branches          ?        1           ",
            f"=========================================",
            f"  Hits              ?        6           ",
            f"  Misses            ?        3           ",
            f"  Partials          ?        1           ",
            f"```",
            f"",
            f"| [Flag](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flags) | Coverage Δ | Complexity Δ | |",
            f"|---|---|---|---|",
            f"| [unit](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `100.00% <100.00%> (?)` | `0.00 <0.00> (?)` | |",
            f"",
            f"Flags with carried forward coverage won't be shown. [Click here](https://docs.codecov.io/docs/carryforward-flags#carryforward-flags-in-the-pull-request-comment) to find out more.",
            f"",
            f"| [Files](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree) | Coverage Δ | Complexity Δ | |",
            f"|---|---|---|---|",
            f"| [file\_1.go](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree#diff-ZmlsZV8xLmdv) | `62.50% <66.67%> (ø)` | `10.00 <0.00> (?)` | |",
            f"",
            f"------",
            f"",
            f"[Continue to review full report in "
            f"Codecov by Sentry](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=continue).",
            f"> **Legend** - [Click here to learn "
            f"more](https://docs.codecov.io/docs/codecov-delta)",
            f"> `Δ = absolute <relative> (impact)`, `ø = not affected`, `? = missing data`",
            f"> Powered by "
            f"[Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=footer). "
            f"Last update "
            f"[{comparison.base.commit.commitid[:7]}...{comparison.head.commit.commitid[:7]}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=lastupdated). "
            f"Read the [comment docs](https://docs.codecov.io/docs/pull-request-comments).",
            f"",
        ]
        for exp, res in zip(expected_result, result):
            assert exp == res
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_build_message_no_base_commit(
        self,
        dbsession,
        mock_configuration,
        mock_repo_provider,
        sample_comparison_without_base_with_pull,
    ):
        mock_configuration.params["setup"]["codecov_dashboard_url"] = "test.example.br"
        comparison = sample_comparison_without_base_with_pull
        pull = comparison.pull
        notifier = CommentNotifier(
            repository=comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={"layout": "reach, diff, flags, files, footer"},
            notifier_site_settings=True,
            current_yaml={},
        )
        repository = comparison.head.commit.repository
        result = await notifier.build_message(comparison)
        expected_result = [
            f"## [Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=h1) Report",
            f"> :exclamation: No coverage uploaded for pull request base (`master@cdf9aa4`). [Click here to learn what that means](https://docs.codecov.io/docs/error-reference#section-missing-base-commit).",
            f"> The diff coverage is `n/a`.",
            f"",
            f"[![Impacted file tree graph](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/graphs/tree.svg?width=650&height=150&src=pr&token={repository.image_token})](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree)",
            f"",
            f"```diff",
            f"@@            Coverage Diff            @@",
            f"##             master      #{pull.pullid}   +/-   ##",
            f"=========================================",
            f"  Coverage          ?   60.00%           ",
            f"  Complexity        ?       10           ",
            f"=========================================",
            f"  Files             ?        2           ",
            f"  Lines             ?       10           ",
            f"  Branches          ?        1           ",
            f"=========================================",
            f"  Hits              ?        6           ",
            f"  Misses            ?        3           ",
            f"  Partials          ?        1           ",
            f"```",
            f"",
            f"| [Flag](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flags) | Coverage Δ | Complexity Δ | |",
            f"|---|---|---|---|",
            f"| [unit](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `100.00% <0.00%> (?)` | `0.00% <0.00%> (?%)` | |",
            f"",
            f"Flags with carried forward coverage won't be shown. [Click here](https://docs.codecov.io/docs/carryforward-flags#carryforward-flags-in-the-pull-request-comment) to find out more.",
            f"",
            f"",
            f"------",
            f"",
            f"[Continue to review full report in "
            f"Codecov by Sentry](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=continue).",
            f"> **Legend** - [Click here to learn "
            f"more](https://docs.codecov.io/docs/codecov-delta)",
            f"> `Δ = absolute <relative> (impact)`, `ø = not affected`, `? = missing data`",
            f"> Powered by "
            f"[Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=footer). "
            f"Last update "
            f"[cdf9aa4...{comparison.head.commit.commitid[:7]}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=lastupdated). "
            f"Read the [comment docs](https://docs.codecov.io/docs/pull-request-comments).",
            f"",
        ]
        for exp, res in zip(expected_result, result):
            assert exp == res
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_build_message_no_change(
        self,
        dbsession,
        mock_configuration,
        mock_repo_provider,
        sample_comparison_no_change,
    ):
        mock_configuration.params["setup"]["codecov_dashboard_url"] = "test.example.br"
        comparison = sample_comparison_no_change
        pull = comparison.pull

        notifier = CommentNotifier(
            repository=comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={"layout": "reach, diff, flags, files, footer"},
            notifier_site_settings=True,
            current_yaml={},
        )
        repository = comparison.head.commit.repository
        result = await notifier.build_message(comparison)

        expected_result = [
            f"## [Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=h1) Report",
            f"> Merging [#{pull.pullid}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=desc) ({comparison.head.commit.commitid[:7]}) into [master](test.example.br/gh/{repository.slug}/commit/{comparison.base.commit.commitid}?el=desc) ({comparison.base.commit.commitid[:7]}) will **not change** coverage.",
            f"> The diff coverage is `66.67%`.",
            f"",
            f"[![Impacted file tree graph](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/graphs/tree.svg?width=650&height=150&src=pr&token={repository.image_token})](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree)",
            f"",
            f"```diff",
            f"@@            Coverage Diff            @@",
            f"##             master      #{pull.pullid}   +/-   ##",
            f"=========================================",
            f"  Coverage     60.00%   60.00%           ",
            f"  Complexity       10       10           ",
            f"=========================================",
            f"  Files             2        2           ",
            f"  Lines            10       10           ",
            f"  Branches          1        1           ",
            f"=========================================",
            f"  Hits              6        6           ",
            f"  Misses            3        3           ",
            f"  Partials          1        1           ",
            f"```",
            f"",
            f"| [Flag](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flags) | Coverage Δ | Complexity Δ | |",
            f"|---|---|---|---|",
            f"| [unit](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `100.00% <100.00%> (ø)` | `0.00 <0.00> (ø)` | |",
            f"",
            f"Flags with carried forward coverage won't be shown. [Click here](https://docs.codecov.io/docs/carryforward-flags#carryforward-flags-in-the-pull-request-comment) to find out more.",
            f"",
            f"| [Files](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree) | Coverage Δ | Complexity Δ | |",
            f"|---|---|---|---|",
            f"| [file\\_1.go](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree#diff-ZmlsZV8xLmdv) | `62.50% <66.67%> (ø)` | `10.00 <0.00> (ø)` | |",
            f"",
            f"------",
            f"",
            f"[Continue to review full report in "
            f"Codecov by Sentry](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=continue).",
            f"> **Legend** - [Click here to learn "
            f"more](https://docs.codecov.io/docs/codecov-delta)",
            f"> `Δ = absolute <relative> (impact)`, `ø = not affected`, `? = missing data`",
            f"> Powered by "
            f"[Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=footer). "
            f"Last update "
            f"[{sample_comparison_no_change.base.commit.commitid[:7]}...{sample_comparison_no_change.head.commit.commitid[:7]}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=lastupdated). "
            f"Read the [comment docs](https://docs.codecov.io/docs/pull-request-comments).",
            f"",
        ]
        print(result)
        li = 0
        for exp, res in zip(expected_result, result):
            li += 1
            print(li)
            assert exp == res
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_build_message_negative_change(
        self,
        dbsession,
        mock_configuration,
        mock_repo_provider,
        sample_comparison_negative_change,
    ):
        mock_configuration.params["setup"]["codecov_dashboard_url"] = "test.example.br"
        comparison = sample_comparison_negative_change
        pull = comparison.pull
        notifier = CommentNotifier(
            repository=comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={"layout": "reach, diff, flags, files, footer"},
            notifier_site_settings=True,
            current_yaml={},
        )
        repository = comparison.head.commit.repository
        result = await notifier.build_message(comparison)
        expected_result = [
            f"## [Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=h1) Report",
            f"> Merging [#{pull.pullid}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=desc) ({comparison.head.commit.commitid[:7]}) into [master](test.example.br/gh/{repository.slug}/commit/{comparison.base.commit.commitid}?el=desc) ({comparison.base.commit.commitid[:7]}) will **decrease** coverage by `10.00%`.",
            f"> The diff coverage is `n/a`.",
            f"",
            f"[![Impacted file tree graph](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/graphs/tree.svg?width=650&height=150&src=pr&token={repository.image_token})](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree)",
            f"",
            f"```diff",
            f"@@              Coverage Diff              @@",
            f"##             master      #{pull.pullid}       +/-   ##",
            f"=============================================",
            f"- Coverage     60.00%   50.00%   -10.00%     ",
            f"- Complexity       10       11        +1     ",
            f"=============================================",
            f"  Files             2        2               ",
            f"  Lines            10        6        -4     ",
            f"  Branches          1        0        -1     ",
            f"=============================================",
            f"- Hits              6        3        -3     ",
            f"  Misses            3        3               ",
            f"+ Partials          1        0        -1     ",
            f"```",
            f"",
            f"| [Flag](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flags) | Coverage Δ | Complexity Δ | |",
            f"|---|---|---|---|",
            f"| [integration](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `100.00% <ø> (?)` | `0.00 <ø> (?)` | |",
            f"| [unit](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `?` | `?` | |",
            f"",
            f"Flags with carried forward coverage won't be shown. [Click here](https://docs.codecov.io/docs/carryforward-flags#carryforward-flags-in-the-pull-request-comment) to find out more.",
            f"",
            f"| [Files](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree) | Coverage Δ | Complexity Δ | |",
            f"|---|---|---|---|",
            f"| [file\\_1.go](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree#diff-ZmlsZV8xLmdv) | `50.00% <ø> (-12.50%)` | `11.00 <0.00> (+1.00)` | :arrow_down: |",
            f"",
            f"... and [1 file with indirect coverage changes](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/indirect-changes?src=pr&el=tree-more)",
            f"",
            f"------",
            f"",
            f"[Continue to review full report in "
            f"Codecov by Sentry](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=continue).",
            f"> **Legend** - [Click here to learn "
            f"more](https://docs.codecov.io/docs/codecov-delta)",
            f"> `Δ = absolute <relative> (impact)`, `ø = not affected`, `? = missing data`",
            f"> Powered by "
            f"[Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=footer). "
            f"Last update "
            f"[{comparison.base.commit.commitid[:7]}...{comparison.head.commit.commitid[:7]}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=lastupdated). "
            f"Read the [comment docs](https://docs.codecov.io/docs/pull-request-comments).",
            f"",
        ]
        print(result)
        for exp, res in zip(expected_result, result):
            assert exp == res
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_build_message_negative_change_tricky_rounding(
        self,
        dbsession,
        mock_configuration,
        mock_repo_provider,
        sample_comparison_negative_change,
    ):
        # This example was taken from a real PR in which we had issues with rounding
        # That's why the numbers will be.... dramatic
        mock_configuration.params["setup"]["codecov_dashboard_url"] = "test.example.br"
        comparison = sample_comparison_negative_change
        pull = comparison.pull
        notifier = CommentNotifier(
            repository=comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={"layout": "diff"},
            notifier_site_settings=True,
            current_yaml={"coverage": {"precision": 2, "round": "down"}},
        )
        repository = comparison.head.commit.repository
        # Change the reports
        new_base_report = Report()
        new_base_file = ReportFile("file.py")
        # Produce numbers that we know can be tricky for rounding
        for i in range(1, 6760):
            new_base_file.append(i, ReportLine.create(coverage=1))
        for i in range(6760, 7631):
            new_base_file.append(i, ReportLine.create(coverage=0))
        new_base_report.append(new_base_file)
        comparison.base.report = ReadOnlyReport.create_from_report(new_base_report)
        new_head_report = Report()
        new_head_file = ReportFile("file.py")
        for i in range(1, 6758):
            new_head_file.append(i, ReportLine.create(coverage=1))
        for i in range(6758, 7632):
            new_head_file.append(i, ReportLine.create(coverage=0))
        new_head_report.append(new_head_file)
        comparison.head.report = ReadOnlyReport.create_from_report(new_head_report)
        result = await notifier.build_message(comparison)
        expected_result = [
            f"## [Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=h1) Report",
            f"> Merging [#{pull.pullid}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=desc) ({comparison.head.commit.commitid[:7]}) into [master](test.example.br/gh/{repository.slug}/commit/{comparison.base.commit.commitid}?el=desc) ({comparison.base.commit.commitid[:7]}) will **decrease** coverage by `0.04%`.",
            f"> The diff coverage is `n/a`.",
            f"",
            f"```diff",
            f"@@            Coverage Diff             @@",
            f"##           master      #{pull.pullid}      +/-   ##",
            f"==========================================",
            f"- Coverage   88.58%   88.54%   -0.04%     ",
            f"==========================================",
            f"  Files           1        1              ",
            f"  Lines        7630     7631       +1     ",
            f"==========================================",
            f"- Hits         6759     6757       -2     ",
            f"- Misses        871      874       +3     ",
            f"```",
            f"",
        ]
        print(result)
        li = 0
        for exp, res in zip(expected_result, result):
            li += 1
            print(li)
            assert exp == res
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_build_message_negative_change_tricky_rounding_newheader(
        self,
        dbsession,
        mock_configuration,
        mock_repo_provider,
        sample_comparison_negative_change,
    ):
        # This example was taken from a real PR in which we had issues with rounding
        # That's why the numbers will be.... dramatic
        mock_configuration.params["setup"]["codecov_dashboard_url"] = "test.example.br"
        comparison = sample_comparison_negative_change
        pull = comparison.pull
        notifier = CommentNotifier(
            repository=comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={"layout": "newheader"},
            notifier_site_settings=True,
            current_yaml={"coverage": {"precision": 2, "round": "down"}},
        )
        repository = comparison.head.commit.repository
        # Change the reports
        new_base_report = Report()
        new_base_file = ReportFile("file.py")
        # Produce numbers that we know can be tricky for rounding
        for i in range(1, 6760):
            new_base_file.append(i, ReportLine.create(coverage=1))
        for i in range(6760, 7631):
            new_base_file.append(i, ReportLine.create(coverage=0))
        new_base_report.append(new_base_file)
        comparison.base.report = ReadOnlyReport.create_from_report(new_base_report)
        new_head_report = Report()
        new_head_file = ReportFile("file.py")
        for i in range(1, 6758):
            new_head_file.append(i, ReportLine.create(coverage=1))
        for i in range(6758, 7632):
            new_head_file.append(i, ReportLine.create(coverage=0))
        new_head_report.append(new_head_file)
        comparison.head.report = ReadOnlyReport.create_from_report(new_head_report)
        result = await notifier.build_message(comparison)
        expected_result = [
            f"## [Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=h1) Report",
            f"All modified and coverable lines are covered by tests :white_check_mark:",
            f"> Comparison is base [(`{comparison.base.commit.commitid[:7]}`)](test.example.br/gh/{repository.slug}/commit/{comparison.base.commit.commitid}?el=desc) 88.58% compared to head [(`{comparison.head.commit.commitid[:7]}`)](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=desc) 88.54%.",
            f"",
        ]
        li = 0
        for exp, res in zip(expected_result, result):
            li += 1
            assert exp == res
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_build_message_show_carriedforward_flags_no_cf_coverage(
        self, dbsession, mock_configuration, mock_repo_provider, sample_comparison
    ):
        mock_configuration.params["setup"]["codecov_dashboard_url"] = "test.example.br"
        comparison = sample_comparison
        pull = comparison.pull
        notifier = CommentNotifier(
            repository=comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "show_carryforward_flags": True,
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        repository = comparison.head.commit.repository
        result = await notifier.build_message(comparison)
        expected_result = [
            f"## [Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=h1) Report",
            f"> Merging [#{pull.pullid}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=desc) ({comparison.head.commit.commitid[:7]}) into [master](test.example.br/gh/{repository.slug}/commit/{sample_comparison.base.commit.commitid}?el=desc) ({sample_comparison.base.commit.commitid[:7]}) will **increase** coverage by `10.00%`.",
            f"> The diff coverage is `66.67%`.",
            f"",
            f"[![Impacted file tree graph](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/graphs/tree.svg?width=650&height=150&src=pr&token={repository.image_token})](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree)",
            f"",
            f"```diff",
            f"@@              Coverage Diff              @@",
            f"##             master      #{pull.pullid}       +/-   ##",
            f"=============================================",
            f"+ Coverage     50.00%   60.00%   +10.00%     ",
            f"+ Complexity       11       10        -1     ",
            f"=============================================",
            f"  Files             2        2               ",
            f"  Lines             6       10        +4     ",
            f"  Branches          0        1        +1     ",
            f"=============================================",
            f"+ Hits              3        6        +3     ",
            f"  Misses            3        3               ",
            f"- Partials          0        1        +1     ",
            f"```",
            f"",
            f"| [Flag](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flags) | Coverage Δ | Complexity Δ | |",
            f"|---|---|---|---|",
            f"| [integration](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `?` | `?` | |",
            f"| [unit](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `100.00% <100.00%> (?)` | `0.00 <0.00> (?)` | |",
            f"",
            f"| [Files](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree) | Coverage Δ | Complexity Δ | |",
            f"|---|---|---|---|",
            f"| [file\\_1.go](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree#diff-ZmlsZV8xLmdv) | `62.50% <66.67%> (+12.50%)` | `10.00 <0.00> (-1.00)` | :arrow_up: |",
            f"",
            f"... and [1 file with indirect coverage changes](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/indirect-changes?src=pr&el=tree-more)",
            f"",
            f"------",
            f"",
            f"[Continue to review full report in "
            f"Codecov by Sentry](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=continue).",
            f"> **Legend** - [Click here to learn "
            f"more](https://docs.codecov.io/docs/codecov-delta)",
            f"> `Δ = absolute <relative> (impact)`, `ø = not affected`, `? = missing data`",
            f"> Powered by "
            f"[Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=footer). "
            f"Last update "
            f"[{sample_comparison.base.commit.commitid[:7]}...{sample_comparison.head.commit.commitid[:7]}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=lastupdated). "
            f"Read the [comment docs](https://docs.codecov.io/docs/pull-request-comments).",
            f"",
        ]
        for exp, res in zip(expected_result, result):
            assert exp == res
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_build_message_with_without_flags(
        self,
        dbsession,
        mock_configuration,
        mock_repo_provider,
        sample_comparison_coverage_carriedforward,
    ):
        # Without flags table
        mock_configuration.params["setup"]["codecov_dashboard_url"] = "test.example.br"
        comparison = sample_comparison_coverage_carriedforward
        pull = comparison.pull
        notifier = CommentNotifier(
            repository=comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, files, footer",
                "show_carryforward_flags": True,
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        repository = comparison.head.commit.repository
        result = await notifier.build_message(comparison)
        expected_result = [
            f"## [Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=h1) Report",
            f"> Merging [#{pull.pullid}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=desc) ({comparison.head.commit.commitid[:7]}) into [master](test.example.br/gh/{repository.slug}/commit/{comparison.base.commit.commitid}?el=desc) ({comparison.base.commit.commitid[:7]}) will **not change** coverage.",
            f"> The diff coverage is `n/a`.",
            f"",
            f"[![Impacted file tree graph](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/graphs/tree.svg?width=650&height=150&src=pr&token={repository.image_token})](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree)",
            f"",
            f"```diff",
            f"@@           Coverage Diff           @@",
            f"##           master      #{pull.pullid}   +/-   ##",
            f"=======================================",
            f"  Coverage   65.38%   65.38%           ",
            f"=======================================",
            f"  Files          15       15           ",
            f"  Lines         208      208           ",
            f"=======================================",
            f"  Hits          136      136           ",
            f"  Misses          4        4           ",
            f"  Partials       68       68           ",
            f"```",
            f"",
            f"",
            f"------",
            f"",
            f"[Continue to review full report in "
            f"Codecov by Sentry](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=continue).",
            f"> **Legend** - [Click here to learn "
            f"more](https://docs.codecov.io/docs/codecov-delta)",
            f"> `Δ = absolute <relative> (impact)`, `ø = not affected`, `? = missing data`",
            f"> Powered by "
            f"[Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=footer). "
            f"Last update "
            f"[{comparison.base.commit.commitid[:7]}...{comparison.head.commit.commitid[:7]}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=lastupdated). "
            f"Read the [comment docs](https://docs.codecov.io/docs/pull-request-comments).",
            f"",
        ]
        print(result)
        li = 0
        for exp, res in zip(expected_result, result):
            li += 1
            print(li)
            assert exp == res
        assert result == expected_result

        # With flags table
        mock_configuration.params["setup"]["codecov_dashboard_url"] = "test.example.br"
        comparison = sample_comparison_coverage_carriedforward
        pull = comparison.pull
        notifier = CommentNotifier(
            repository=comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "show_carryforward_flags": True,
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        repository = comparison.head.commit.repository
        result = await notifier.build_message(comparison)
        expected_result = [
            f"## [Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=h1) Report",
            f"> Merging [#{pull.pullid}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=desc) ({comparison.head.commit.commitid[:7]}) into [master](test.example.br/gh/{repository.slug}/commit/{comparison.base.commit.commitid}?el=desc) ({comparison.base.commit.commitid[:7]}) will **not change** coverage.",
            f"> The diff coverage is `n/a`.",
            f"",
            f"[![Impacted file tree graph](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/graphs/tree.svg?width=650&height=150&src=pr&token={repository.image_token})](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree)",
            f"",
            f"```diff",
            f"@@           Coverage Diff           @@",
            f"##           master      #{pull.pullid}   +/-   ##",
            f"=======================================",
            f"  Coverage   65.38%   65.38%           ",
            f"=======================================",
            f"  Files          15       15           ",
            f"  Lines         208      208           ",
            f"=======================================",
            f"  Hits          136      136           ",
            f"  Misses          4        4           ",
            f"  Partials       68       68           ",
            f"```",
            f"",
            f"| [Flag](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flags) | Coverage Δ | | *Carryforward flag |",
            f"|---|---|---|---|",
            f"| [enterprise](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `25.00% <ø> (ø)` | | Carriedforward from [1234567](test.example.br/gh/{repository.slug}/commit/123456789sha) |",
            f"| [integration](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `25.00% <ø> (ø)` | | Carriedforward |",
            f"| [unit](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `25.00% <ø> (ø)` | | |",
            f"",
            f"*This pull request uses carry forward flags. [Click here](https://docs.codecov.io/docs/carryforward-flags) to find out more."
            f"",
            f"",
            f"",
            f"------",
            f"",
            f"[Continue to review full report in "
            f"Codecov by Sentry](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=continue).",
            f"> **Legend** - [Click here to learn "
            f"more](https://docs.codecov.io/docs/codecov-delta)",
            f"> `Δ = absolute <relative> (impact)`, `ø = not affected`, `? = missing data`",
            f"> Powered by "
            f"[Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=footer). "
            f"Last update "
            f"[{comparison.base.commit.commitid[:7]}...{comparison.head.commit.commitid[:7]}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=lastupdated). "
            f"Read the [comment docs](https://docs.codecov.io/docs/pull-request-comments).",
            f"",
        ]
        print(result)
        li = 0
        for exp, res in zip(expected_result, result):
            li += 1
            print(li)
            assert exp == res
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_build_message_show_carriedforward_flags_has_cf_coverage(
        self,
        dbsession,
        mock_configuration,
        mock_repo_provider,
        sample_comparison_coverage_carriedforward,
    ):
        mock_configuration.params["setup"]["codecov_dashboard_url"] = "test.example.br"
        comparison = sample_comparison_coverage_carriedforward
        pull = comparison.pull
        notifier = CommentNotifier(
            repository=comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "show_carryforward_flags": True,
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        repository = comparison.head.commit.repository
        result = await notifier.build_message(comparison)
        expected_result = [
            f"## [Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=h1) Report",
            f"> Merging [#{pull.pullid}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=desc) ({comparison.head.commit.commitid[:7]}) into [master](test.example.br/gh/{repository.slug}/commit/{comparison.base.commit.commitid}?el=desc) ({comparison.base.commit.commitid[:7]}) will **not change** coverage.",
            f"> The diff coverage is `n/a`.",
            f"",
            f"[![Impacted file tree graph](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/graphs/tree.svg?width=650&height=150&src=pr&token={repository.image_token})](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree)",
            f"",
            f"```diff",
            f"@@           Coverage Diff           @@",
            f"##           master      #{pull.pullid}   +/-   ##",
            f"=======================================",
            f"  Coverage   65.38%   65.38%           ",
            f"=======================================",
            f"  Files          15       15           ",
            f"  Lines         208      208           ",
            f"=======================================",
            f"  Hits          136      136           ",
            f"  Misses          4        4           ",
            f"  Partials       68       68           ",
            f"```",
            f"",
            f"| [Flag](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flags) | Coverage Δ | | *Carryforward flag |",
            f"|---|---|---|---|",
            f"| [enterprise](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `25.00% <ø> (ø)` | | Carriedforward from [1234567](test.example.br/gh/{repository.slug}/commit/123456789sha) |",
            f"| [integration](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `25.00% <ø> (ø)` | | Carriedforward |",
            f"| [unit](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `25.00% <ø> (ø)` | | |",
            f"",
            f"*This pull request uses carry forward flags. [Click here](https://docs.codecov.io/docs/carryforward-flags) to find out more."
            f"",
            f"",
            f"",
            f"------",
            f"",
            f"[Continue to review full report in "
            f"Codecov by Sentry](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=continue).",
            f"> **Legend** - [Click here to learn "
            f"more](https://docs.codecov.io/docs/codecov-delta)",
            f"> `Δ = absolute <relative> (impact)`, `ø = not affected`, `? = missing data`",
            f"> Powered by "
            f"[Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=footer). "
            f"Last update "
            f"[{comparison.base.commit.commitid[:7]}...{comparison.head.commit.commitid[:7]}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=lastupdated). "
            f"Read the [comment docs](https://docs.codecov.io/docs/pull-request-comments).",
            f"",
        ]
        print(result)
        li = 0
        for exp, res in zip(expected_result, result):
            li += 1
            print(li)
            assert exp == res
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_build_message_hide_carriedforward_flags_has_cf_coverage(
        self,
        dbsession,
        mock_configuration,
        mock_repo_provider,
        sample_comparison_coverage_carriedforward,
    ):
        mock_configuration.params["setup"]["codecov_dashboard_url"] = "test.example.br"
        comparison = sample_comparison_coverage_carriedforward
        pull = comparison.pull
        notifier = CommentNotifier(
            repository=comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "show_carryforward_flags": False,
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        repository = comparison.head.commit.repository
        result = await notifier.build_message(comparison)
        expected_result = [
            f"## [Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=h1) Report",
            f"> Merging [#{pull.pullid}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=desc) ({comparison.head.commit.commitid[:7]}) into [master](test.example.br/gh/{repository.slug}/commit/{comparison.base.commit.commitid}?el=desc) ({comparison.base.commit.commitid[:7]}) will **not change** coverage.",
            f"> The diff coverage is `n/a`.",
            f"",
            f"[![Impacted file tree graph](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/graphs/tree.svg?width=650&height=150&src=pr&token={repository.image_token})](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree)",
            f"",
            f"```diff",
            f"@@           Coverage Diff           @@",
            f"##           master      #{pull.pullid}   +/-   ##",
            f"=======================================",
            f"  Coverage   65.38%   65.38%           ",
            f"=======================================",
            f"  Files          15       15           ",
            f"  Lines         208      208           ",
            f"=======================================",
            f"  Hits          136      136           ",
            f"  Misses          4        4           ",
            f"  Partials       68       68           ",
            f"```",
            f"",
            f"| [Flag](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flags) | Coverage Δ | |",
            f"|---|---|---|",
            f"| [unit](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `25.00% <ø> (ø)` | |",
            f"",
            f"Flags with carried forward coverage won't be shown. [Click here](https://docs.codecov.io/docs/carryforward-flags#carryforward-flags-in-the-pull-request-comment) to find out more."
            f"",
            f"",
            f"",
            f"------",
            f"",
            f"[Continue to review full report in "
            f"Codecov by Sentry](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=continue).",
            f"> **Legend** - [Click here to learn "
            f"more](https://docs.codecov.io/docs/codecov-delta)",
            f"> `Δ = absolute <relative> (impact)`, `ø = not affected`, `? = missing data`",
            f"> Powered by "
            f"[Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=footer). "
            f"Last update "
            f"[{comparison.base.commit.commitid[:7]}...{comparison.head.commit.commitid[:7]}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=lastupdated). "
            f"Read the [comment docs](https://docs.codecov.io/docs/pull-request-comments).",
            f"",
        ]
        print(result)
        li = 0
        for exp, res in zip(expected_result, result):
            li += 1
            print(li)
            assert exp == res
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_send_actual_notification_spammy(
        self, dbsession, mock_configuration, mock_repo_provider, sample_comparison
    ):
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "spammy",
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        data = {"message": ["message"], "commentid": "12345", "pullid": 98}
        mock_repo_provider.post_comment.return_value = {"id": 9865}
        result = await notifier.send_actual_notification(data)
        assert result.notification_attempted
        assert result.notification_successful
        assert result.explanation is None
        assert result.data_sent == data
        assert result.data_received == {"id": 9865}
        mock_repo_provider.post_comment.assert_called_with(98, "message")
        assert not mock_repo_provider.edit_comment.called
        assert not mock_repo_provider.delete_comment.called

    @pytest.mark.asyncio
    async def test_build_message_no_flags(
        self,
        dbsession,
        mock_configuration,
        mock_repo_provider,
        sample_report_without_flags,
        sample_comparison,
    ):
        mock_configuration.params["setup"]["codecov_dashboard_url"] = "test.example.br"
        pull = sample_comparison.pull
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={"layout": "reach, diff, flags, files, footer"},
            notifier_site_settings=True,
            current_yaml={},
        )
        sample_comparison.head.report = ReadOnlyReport.create_from_report(
            sample_report_without_flags
        )
        comparison = sample_comparison
        repository = sample_comparison.head.commit.repository
        result = await notifier.build_message(sample_comparison)
        expected_result = [
            f"## [Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=h1) Report",
            f"> Merging [#{pull.pullid}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=desc) ({comparison.head.commit.commitid[:7]}) into [master](test.example.br/gh/{repository.slug}/commit/{sample_comparison.base.commit.commitid}?el=desc) ({comparison.base.commit.commitid[:7]}) will **increase** coverage by `10.00%`.",
            f"> The diff coverage is `66.67%`.",
            f"",
            f"[![Impacted file tree graph](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/graphs/tree.svg?width=650&height=150&src=pr&token={repository.image_token})](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree)",
            f"",
            f"```diff",
            f"@@              Coverage Diff              @@",
            f"##             master      #{pull.pullid}       +/-   ##",
            f"=============================================",
            f"+ Coverage     50.00%   60.00%   +10.00%     ",
            f"+ Complexity       11       10        -1     ",
            f"=============================================",
            f"  Files             2        2               ",
            f"  Lines             6       10        +4     ",
            f"  Branches          0        1        +1     ",
            f"=============================================",
            f"+ Hits              3        6        +3     ",
            f"  Misses            3        3               ",
            f"- Partials          0        1        +1     ",
            f"```",
            f"",
            f"| [Flag](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flags) | Coverage Δ | Complexity Δ | |",
            f"|---|---|---|---|",
            f"| [integration](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `?` | `?` | |",
            f"",
            f"Flags with carried forward coverage won't be shown. [Click here](https://docs.codecov.io/docs/carryforward-flags#carryforward-flags-in-the-pull-request-comment) to find out more.",
            f"",
            f"| [Files](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree) | Coverage Δ | Complexity Δ | |",
            f"|---|---|---|---|",
            f"| [file\\_1.go](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree#diff-ZmlsZV8xLmdv) | `62.50% <66.67%> (+12.50%)` | `10.00 <0.00> (-1.00)` | :arrow_up: |",
            f"",
            f"... and [1 file with indirect coverage changes](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/indirect-changes?src=pr&el=tree-more)",
            f"",
            f"------",
            f"",
            f"[Continue to review full report in "
            f"Codecov by Sentry](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=continue).",
            f"> **Legend** - [Click here to learn "
            f"more](https://docs.codecov.io/docs/codecov-delta)",
            f"> `Δ = absolute <relative> (impact)`, `ø = not affected`, `? = missing data`",
            f"> Powered by "
            f"[Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=footer). "
            f"Last update "
            f"[{comparison.base.commit.commitid[:7]}...{comparison.head.commit.commitid[:7]}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=lastupdated). "
            f"Read the [comment docs](https://docs.codecov.io/docs/pull-request-comments).",
            f"",
        ]
        for exp, res in zip(expected_result, result):
            assert exp == res
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_send_actual_notification_new_no_permissions(
        self, dbsession, mock_configuration, mock_repo_provider, sample_comparison
    ):
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "new",
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        data = {"message": ["message"], "commentid": "12345", "pullid": 98}
        mock_repo_provider.post_comment.return_value = {"id": 9865}
        mock_repo_provider.delete_comment.side_effect = TorngitClientError(
            "code", "response", "message"
        )
        result = await notifier.send_actual_notification(data)
        assert result.notification_attempted
        assert not result.notification_successful
        assert result.explanation == "no_permissions"
        assert result.data_sent == data
        assert result.data_received is None
        mock_repo_provider.delete_comment.assert_called_with(98, "12345")
        assert not mock_repo_provider.post_comment.called
        assert not mock_repo_provider.edit_comment.called

    @pytest.mark.asyncio
    async def test_send_actual_notification_new(
        self, dbsession, mock_configuration, mock_repo_provider, sample_comparison
    ):
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "new",
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        data = {"message": ["message"], "commentid": "12345", "pullid": 98}
        mock_repo_provider.post_comment.return_value = {"id": 9865}
        mock_repo_provider.delete_comment.return_value = True
        result = await notifier.send_actual_notification(data)
        assert result.notification_attempted
        assert result.notification_successful
        assert result.explanation is None
        assert result.data_sent == data
        assert result.data_received == {"id": 9865}
        mock_repo_provider.post_comment.assert_called_with(98, "message")
        assert not mock_repo_provider.edit_comment.called
        mock_repo_provider.delete_comment.assert_called_with(98, "12345")

    @pytest.mark.asyncio
    async def test_send_actual_notification_new_no_permissions_post(
        self, dbsession, mock_configuration, mock_repo_provider, sample_comparison
    ):
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "new",
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        data = {"message": ["message"], "commentid": None, "pullid": 98}
        mock_repo_provider.post_comment.side_effect = TorngitClientError(
            "code", "response", "message"
        )
        mock_repo_provider.edit_comment.side_effect = TorngitClientError(
            "code", "response", "message"
        )
        result = await notifier.send_actual_notification(data)
        assert result.notification_attempted
        assert not result.notification_successful
        assert result.explanation == "comment_posting_permissions"
        assert result.data_sent == data
        assert result.data_received is None
        mock_repo_provider.post_comment.assert_called_with(98, "message")
        assert not mock_repo_provider.delete_comment.called
        assert not mock_repo_provider.edit_comment.called

    @pytest.mark.asyncio
    async def test_send_actual_notification_new_deleted_comment(
        self, dbsession, mock_configuration, mock_repo_provider, sample_comparison
    ):
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "new",
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        data = {"message": ["message"], "commentid": "12345", "pullid": 98}
        mock_repo_provider.post_comment.return_value = {"id": 9865}
        mock_repo_provider.delete_comment.side_effect = TorngitObjectNotFoundError(
            "response", "message"
        )
        result = await notifier.send_actual_notification(data)
        assert result.notification_attempted
        assert result.notification_successful
        assert result.explanation is None
        assert result.data_sent == data
        assert result.data_received == {"id": 9865}
        mock_repo_provider.post_comment.assert_called_with(98, "message")
        assert not mock_repo_provider.edit_comment.called
        mock_repo_provider.delete_comment.assert_called_with(98, "12345")

    @pytest.mark.asyncio
    async def test_send_actual_notification_once_deleted_comment(
        self, dbsession, mock_configuration, mock_repo_provider, sample_comparison
    ):
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "once",
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        data = {"message": ["message"], "commentid": "12345", "pullid": 98}
        mock_repo_provider.post_comment.return_value = {"id": 9865}
        mock_repo_provider.edit_comment.side_effect = TorngitObjectNotFoundError(
            "response", "message"
        )
        result = await notifier.send_actual_notification(data)
        assert not result.notification_attempted
        assert result.notification_successful is None
        assert result.explanation == "comment_deleted"
        assert result.data_sent == data
        assert result.data_received is None
        assert not mock_repo_provider.post_comment.called
        mock_repo_provider.edit_comment.assert_called_with(98, "12345", "message")
        assert not mock_repo_provider.delete_comment.called

    @pytest.mark.asyncio
    async def test_send_actual_notification_once_non_existing_comment(
        self, dbsession, mock_configuration, mock_repo_provider, sample_comparison
    ):
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "once",
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        data = {"message": ["message"], "commentid": None, "pullid": 98}
        mock_repo_provider.post_comment.return_value = {"id": 9865}
        mock_repo_provider.edit_comment.side_effect = TorngitObjectNotFoundError(
            "response", "message"
        )
        result = await notifier.send_actual_notification(data)
        assert result.notification_attempted
        assert result.notification_successful
        assert result.explanation is None
        assert result.data_sent == data
        assert result.data_received == {"id": 9865}
        mock_repo_provider.post_comment.assert_called_with(98, "message")
        assert not mock_repo_provider.delete_comment.called
        assert not mock_repo_provider.edit_comment.called

    @pytest.mark.asyncio
    async def test_send_actual_notification_once(
        self, dbsession, mock_configuration, mock_repo_provider, sample_comparison
    ):
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "once",
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        data = {"message": ["message"], "commentid": "12345", "pullid": 98}
        mock_repo_provider.post_comment.return_value = {"id": 9865}
        mock_repo_provider.edit_comment.return_value = {"id": "49"}
        result = await notifier.send_actual_notification(data)
        assert result.notification_attempted
        assert result.notification_successful
        assert result.explanation is None
        assert result.data_sent == data
        assert result.data_received == {"id": "49"}
        assert not mock_repo_provider.post_comment.called
        mock_repo_provider.edit_comment.assert_called_with(98, "12345", "message")
        assert not mock_repo_provider.delete_comment.called

    @pytest.mark.asyncio
    async def test_send_actual_notification_once_no_permissions(
        self, dbsession, mock_configuration, mock_repo_provider, sample_comparison
    ):
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "once",
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        data = {"message": ["message"], "commentid": "12345", "pullid": 98}
        mock_repo_provider.post_comment.return_value = {"id": 9865}
        mock_repo_provider.edit_comment.side_effect = TorngitClientError(
            "code", "response", "message"
        )
        result = await notifier.send_actual_notification(data)
        assert result.notification_attempted
        assert not result.notification_successful
        assert result.explanation == "no_permissions"
        assert result.data_sent == data
        assert result.data_received is None
        assert not mock_repo_provider.post_comment.called
        mock_repo_provider.edit_comment.assert_called_with(98, "12345", "message")
        assert not mock_repo_provider.delete_comment.called

    @pytest.mark.asyncio
    async def test_send_actual_notification_default(
        self, dbsession, mock_configuration, mock_repo_provider, sample_comparison
    ):
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "default",
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        data = {"message": ["message"], "commentid": "12345", "pullid": 98}
        mock_repo_provider.post_comment.return_value = {"id": 9865}
        mock_repo_provider.edit_comment.return_value = {"id": "49"}
        result = await notifier.send_actual_notification(data)
        assert result.notification_attempted
        assert result.notification_successful
        assert result.explanation is None
        assert result.data_sent == data
        assert result.data_received == {"id": "49"}
        assert not mock_repo_provider.post_comment.called
        mock_repo_provider.edit_comment.assert_called_with(98, "12345", "message")
        assert not mock_repo_provider.delete_comment.called

    @pytest.mark.asyncio
    async def test_send_actual_notification_default_no_permissions_edit(
        self, dbsession, mock_configuration, mock_repo_provider, sample_comparison
    ):
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "default",
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        data = {"message": ["message"], "commentid": "12345", "pullid": 98}
        mock_repo_provider.post_comment.return_value = {"id": 9865}
        mock_repo_provider.edit_comment.side_effect = TorngitClientError(
            "code", "response", "message"
        )
        result = await notifier.send_actual_notification(data)
        assert result.notification_attempted
        assert result.notification_successful
        assert result.explanation is None
        assert result.data_sent == data
        assert result.data_received == {"id": 9865}
        mock_repo_provider.post_comment.assert_called_with(98, "message")
        mock_repo_provider.edit_comment.assert_called_with(98, "12345", "message")
        assert not mock_repo_provider.delete_comment.called

    @pytest.mark.asyncio
    async def test_send_actual_notification_default_no_permissions_twice(
        self, dbsession, mock_configuration, mock_repo_provider, sample_comparison
    ):
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "default",
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        data = {"message": ["message"], "commentid": "12345", "pullid": 98}
        mock_repo_provider.post_comment.side_effect = TorngitClientError(
            "code", "response", "message"
        )
        mock_repo_provider.edit_comment.side_effect = TorngitClientError(
            "code", "response", "message"
        )
        result = await notifier.send_actual_notification(data)
        assert result.notification_attempted
        assert not result.notification_successful
        assert result.explanation == "comment_posting_permissions"
        assert result.data_sent == data
        assert result.data_received is None
        mock_repo_provider.post_comment.assert_called_with(98, "message")
        mock_repo_provider.edit_comment.assert_called_with(98, "12345", "message")
        assert not mock_repo_provider.delete_comment.called

    @pytest.mark.asyncio
    async def test_send_actual_notification_default_comment_not_found(
        self, dbsession, mock_configuration, mock_repo_provider, sample_comparison
    ):
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "default",
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        data = {"message": ["message"], "commentid": "12345", "pullid": 98}
        mock_repo_provider.post_comment.return_value = {"id": 9865}
        mock_repo_provider.edit_comment.side_effect = TorngitObjectNotFoundError(
            "response", "message"
        )
        result = await notifier.send_actual_notification(data)
        assert result.notification_attempted
        assert result.notification_successful
        assert result.explanation is None
        assert result.data_sent == data
        assert result.data_received == {"id": 9865}
        mock_repo_provider.edit_comment.assert_called_with(98, "12345", "message")
        mock_repo_provider.post_comment.assert_called_with(98, "message")
        assert not mock_repo_provider.delete_comment.called

    @pytest.mark.asyncio
    async def test_notify_no_pull_request(
        self, dbsession, sample_comparison_without_pull
    ):
        notifier = CommentNotifier(
            repository=sample_comparison_without_pull.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "default",
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        result = await notifier.notify(sample_comparison_without_pull)
        assert not result.notification_attempted
        assert result.notification_successful is None
        assert result.explanation == "no_pull_request"
        assert result.data_sent is None
        assert result.data_received is None

    @pytest.mark.asyncio
    async def test_notify_pull_head_doesnt_match(self, dbsession, sample_comparison):
        sample_comparison.pull.head = "aaaaaaaaaa"
        dbsession.flush()
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "default",
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        result = await notifier.notify(sample_comparison)
        assert not result.notification_attempted
        assert result.notification_successful is None
        assert result.explanation == "pull_head_does_not_match"
        assert result.data_sent is None
        assert result.data_received is None

    @pytest.mark.asyncio
    async def test_notify_pull_request_not_in_provider(
        self, dbsession, sample_comparison_database_pull_without_provider
    ):
        notifier = CommentNotifier(
            repository=sample_comparison_database_pull_without_provider.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "default",
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        result = await notifier.notify(sample_comparison_database_pull_without_provider)
        assert not result.notification_attempted
        assert result.notification_successful is None
        assert result.explanation == "pull_request_not_in_provider"
        assert result.data_sent is None
        assert result.data_received is None

    @pytest.mark.asyncio
    async def test_notify_server_unreachable(
        self, mocker, dbsession, sample_comparison
    ):
        mocked_send_actual_notification = mocker.patch.object(
            CommentNotifier,
            "send_actual_notification",
            side_effect=TorngitServerUnreachableError(),
        )
        mocked_build_message = mocker.patch.object(
            CommentNotifier, "build_message", return_value=["title", "content"]
        )
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "default",
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        result = await notifier.notify(sample_comparison)
        assert result.notification_attempted
        assert not result.notification_successful
        assert result.explanation == "provider_issue"
        assert result.data_sent == {
            "commentid": None,
            "message": ["title", "content"],
            "pullid": sample_comparison.pull.pullid,
        }
        assert result.data_received is None

    @pytest.mark.asyncio
    async def test_store_results(self, dbsession, sample_comparison):
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "default",
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        result = NotificationResult(
            notification_attempted=True,
            notification_successful=True,
            explanation=None,
            data_sent=None,
            data_received={"id": 578263422},
        )
        notifier.store_results(sample_comparison, result)
        assert sample_comparison.pull.commentid == 578263422
        dbsession.flush()
        assert sample_comparison.pull.commentid == 578263422
        dbsession.refresh(sample_comparison.pull)
        assert sample_comparison.pull.commentid == "578263422"

    @pytest.mark.asyncio
    async def test_store_results_deleted_comment(self, dbsession, sample_comparison):
        sample_comparison.pull.commentid = 12
        dbsession.flush()
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "default",
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        result = NotificationResult(
            notification_attempted=True,
            notification_successful=True,
            explanation=None,
            data_sent=None,
            data_received={"deleted_comment": True},
        )
        notifier.store_results(sample_comparison, result)
        assert sample_comparison.pull.commentid is None
        dbsession.flush()
        assert sample_comparison.pull.commentid is None
        dbsession.refresh(sample_comparison.pull)
        assert sample_comparison.pull.commentid is None

    @pytest.mark.asyncio
    async def test_store_results_no_succesfull_result(
        self, dbsession, sample_comparison
    ):
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "default",
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        result = NotificationResult(
            notification_attempted=True,
            notification_successful=False,
            explanation=None,
            data_sent=None,
            data_received={"id": "yadayada"},
        )
        notifier.store_results(sample_comparison, result)
        assert sample_comparison.pull.commentid is None
        dbsession.flush()
        assert sample_comparison.pull.commentid is None
        dbsession.refresh(sample_comparison.pull)
        assert sample_comparison.pull.commentid is None

    @pytest.mark.asyncio
    async def test_notify_closed_pull_request(self, dbsession, sample_comparison):
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "default",
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        sample_comparison.pull.state = "closed"
        dbsession.flush()
        dbsession.refresh(sample_comparison.pull)
        result = await notifier.notify(sample_comparison)
        assert not result.notification_attempted
        assert result.notification_successful is None
        assert result.explanation == "pull_request_closed"
        assert result.data_sent is None
        assert result.data_received is None

    @pytest.mark.asyncio
    async def test_notify_unable_to_fetch_info(
        self, dbsession, mocker, sample_comparison
    ):
        mocked_build_message = mocker.patch.object(
            CommentNotifier,
            "build_message",
            side_effect=TorngitClientError("code", "response", "message"),
        )
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "default",
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        result = await notifier.notify(sample_comparison)
        assert not result.notification_attempted
        assert result.notification_successful is None
        assert result.explanation == "unable_build_message"
        assert result.data_sent is None
        assert result.data_received is None

    @pytest.mark.asyncio
    async def test_notify_not_enough_builds(self, dbsession, sample_comparison):
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "default",
                "after_n_builds": 5,
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        result = await notifier.notify(sample_comparison)
        assert not result.notification_attempted
        assert result.notification_successful is None
        assert result.explanation == "not_enough_builds"
        assert result.data_sent is None
        assert result.data_received is None

    @pytest.mark.asyncio
    async def test_notify_with_enough_builds(
        self, dbsession, sample_comparison, mocker
    ):
        build_message_mocker = mocker.patch.object(
            CommentNotifier,
            "build_message",
            return_value="message_test_notify_with_enough_builds",
        )
        send_comment_default_behavior_mocker = mocker.patch.object(
            CommentNotifier,
            "send_comment_default_behavior",
            return_value=dict(
                notification_attempted=True,
                notification_successful=True,
                explanation=None,
                data_received=None,
            ),
        )
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "default",
                "after_n_builds": 1,
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        result = await notifier.notify(sample_comparison)
        assert result.notification_attempted
        assert result.notification_successful
        assert result.explanation is None
        assert result.data_sent == {
            "commentid": None,
            "message": "message_test_notify_with_enough_builds",
            "pullid": sample_comparison.pull.pullid,
        }
        assert result.data_received is None

    @pytest.mark.asyncio
    async def test_has_enough_changes(self, sample_comparison, mock_repo_provider):
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "default",
                "after_n_builds": 1,
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        assert await notifier.has_enough_changes(sample_comparison)

    @pytest.mark.asyncio
    async def test_has_enough_changes_no_diff(
        self, sample_comparison_without_base_report, mock_repo_provider
    ):
        mock_repo_provider.get_compare.return_value = {"diff": None}
        notifier = CommentNotifier(
            repository=sample_comparison_without_base_report.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "default",
                "after_n_builds": 1,
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        assert not (
            await notifier.has_enough_changes(sample_comparison_without_base_report)
        )

    @pytest.mark.asyncio
    async def test_has_enough_changes_exact_same_report_diff_intersection_report(
        self, sample_comparison_no_change, mock_repo_provider
    ):
        notifier = CommentNotifier(
            repository=sample_comparison_no_change.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "default",
                "after_n_builds": 1,
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        assert await notifier.has_enough_changes(sample_comparison_no_change)

    @pytest.mark.asyncio
    async def test_has_enough_changes_exact_same_report_diff_unrelated_report(
        self, sample_comparison_no_change, mock_repo_provider
    ):
        compare_result = {
            "diff": {
                "files": {
                    "README.md": {
                        "type": "modified",
                        "before": None,
                        "segments": [
                            {
                                "header": ["5", "8", "5", "9"],
                                "lines": [
                                    " Overview",
                                    " --------",
                                    " ",
                                    "-Main website: `Codecov <https://codecov.io/>`_.",
                                    "-Main website: `Codecov <https://codecov.io/>`_.",
                                    "+",
                                    "+website: `Codecov <https://codecov.io/>`_.",
                                    "+website: `Codecov <https://codecov.io/>`_.",
                                    " ",
                                    " .. code-block:: shell-session",
                                    " ",
                                ],
                            },
                            {
                                "header": ["46", "12", "47", "19"],
                                "lines": [
                                    " ",
                                    " You may need to configure a ``.coveragerc`` file. Learn more `here <http://coverage.readthedocs.org/en/latest/config.html>`_. Start with this `generic .coveragerc <https://gist.github.com/codecov-io/bf15bde2c7db1a011b6e>`_ for example.",
                                    " -",
                                ],
                            },
                        ],
                        "stats": {"added": 11, "removed": 4},
                    }
                }
            }
        }
        mock_repo_provider.get_compare.return_value = compare_result
        notifier = CommentNotifier(
            repository=sample_comparison_no_change.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "default",
                "after_n_builds": 1,
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        assert not (await notifier.has_enough_changes(sample_comparison_no_change))

    @pytest.mark.asyncio
    async def test_has_enough_changes_exact_same_report_where_diff_has_covered_lines(
        self, sample_comparison_no_change, mock_repo_provider
    ):
        compare_result = {
            "diff": {
                "files": {
                    "file_1.go": {
                        "type": "modified",
                        "before": None,
                        "segments": [
                            {
                                "header": ["4", "7", "4", "7"],
                                "lines": [
                                    " ",
                                    "-Overview",
                                    "---------",
                                    "-",
                                    "-Main website: `Codecov <https://codecov.io/>`_.",
                                    "-Main website: `Codecov <https://codecov.io/>`_.",
                                    "+",
                                    "+website: `Codecov <https://codecov.io/>`_.",
                                    "+website: `Codecov <https://codecov.io/>`_.",
                                    "+",
                                    "+.. code-block:: shell-session",
                                    "+",
                                    "-",
                                ],
                            },
                            {
                                "header": ["46", "12", "47", "19"],
                                "lines": [
                                    " ",
                                    " You may need to configure a ``.coveragerc`` file. Learn more `here <http://coverage.readthedocs.org/en/latest/config.html>`_. Start with this `generic .coveragerc <https://gist.github.com/codecov-io/bf15bde2c7db1a011b6e>`_ for example.",
                                    " -",
                                ],
                            },
                        ],
                        "stats": {"added": 11, "removed": 4},
                    }
                }
            }
        }
        mock_repo_provider.get_compare.return_value = compare_result
        notifier = CommentNotifier(
            repository=sample_comparison_no_change.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "default",
                "after_n_builds": 1,
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        assert await notifier.has_enough_changes(sample_comparison_no_change)

    @pytest.mark.asyncio
    async def test_notify_exact_same_report_diff_unrelated_report(
        self, sample_comparison_no_change, mock_repo_provider
    ):
        compare_result = {
            "diff": {
                "files": {
                    "README.md": {
                        "type": "modified",
                        "before": None,
                        "segments": [
                            {
                                "header": ["5", "8", "5", "9"],
                                "lines": [
                                    " Overview",
                                    " --------",
                                    " ",
                                    "-Main website: `Codecov <https://codecov.io/>`_.",
                                    "-Main website: `Codecov <https://codecov.io/>`_.",
                                    "+",
                                    "+website: `Codecov <https://codecov.io/>`_.",
                                    "+website: `Codecov <https://codecov.io/>`_.",
                                    " ",
                                    " .. code-block:: shell-session",
                                    " ",
                                ],
                            },
                            {
                                "header": ["46", "12", "47", "19"],
                                "lines": [
                                    " ",
                                    " You may need to configure a ``.coveragerc`` file. Learn more `here <http://coverage.readthedocs.org/en/latest/config.html>`_. Start with this `generic .coveragerc <https://gist.github.com/codecov-io/bf15bde2c7db1a011b6e>`_ for example.",
                                    " -",
                                ],
                            },
                        ],
                        "stats": {"added": 11, "removed": 4},
                    }
                }
            }
        }
        mock_repo_provider.get_compare.return_value = compare_result
        notifier = CommentNotifier(
            repository=sample_comparison_no_change.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "default",
                "after_n_builds": 1,
                "require_changes": True,
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        res = await notifier.notify(sample_comparison_no_change)
        assert res.notification_attempted is False
        assert res.notification_successful is None
        assert res.explanation == "changes_required"
        assert res.data_sent is None
        assert res.data_received is None

    @pytest.mark.asyncio
    async def test_notify_exact_same_report_diff_unrelated_report_deleting_comment(
        self, sample_comparison_no_change, mock_repo_provider
    ):
        compare_result = {
            "diff": {
                "files": {
                    "README.md": {
                        "type": "modified",
                        "before": None,
                        "segments": [
                            {
                                "header": ["5", "8", "5", "9"],
                                "lines": [
                                    " Overview",
                                    " --------",
                                    " ",
                                    "-Main website: `Codecov <https://codecov.io/>`_.",
                                    "-Main website: `Codecov <https://codecov.io/>`_.",
                                    "+",
                                    "+website: `Codecov <https://codecov.io/>`_.",
                                    "+website: `Codecov <https://codecov.io/>`_.",
                                    " ",
                                    " .. code-block:: shell-session",
                                    " ",
                                ],
                            },
                            {
                                "header": ["46", "12", "47", "19"],
                                "lines": [
                                    " ",
                                    " You may need to configure a ``.coveragerc`` file. Learn more `here <http://coverage.readthedocs.org/en/latest/config.html>`_. Start with this `generic .coveragerc <https://gist.github.com/codecov-io/bf15bde2c7db1a011b6e>`_ for example.",
                                    " -",
                                ],
                            },
                        ],
                        "stats": {"added": 11, "removed": 4},
                    }
                }
            }
        }
        mock_repo_provider.get_compare.return_value = compare_result
        sample_comparison_no_change.pull.commentid = 12
        notifier = CommentNotifier(
            repository=sample_comparison_no_change.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "default",
                "after_n_builds": 1,
                "require_changes": True,
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        res = await notifier.notify(sample_comparison_no_change)
        assert res.notification_attempted is False
        assert res.notification_successful is None
        assert res.explanation == "changes_required"
        assert res.data_sent is None
        assert res.data_received == {"deleted_comment": True}

    @pytest.mark.asyncio
    async def test_notify_exact_same_report_diff_unrelated_report_deleting_comment_cant_delete(
        self, sample_comparison_no_change, mock_repo_provider
    ):
        compare_result = {
            "diff": {
                "files": {
                    "README.md": {
                        "type": "modified",
                        "before": None,
                        "segments": [
                            {
                                "header": ["5", "8", "5", "9"],
                                "lines": [
                                    " Overview",
                                    " --------",
                                    " ",
                                    "-Main website: `Codecov <https://codecov.io/>`_.",
                                    "-Main website: `Codecov <https://codecov.io/>`_.",
                                    "+",
                                    "+website: `Codecov <https://codecov.io/>`_.",
                                    "+website: `Codecov <https://codecov.io/>`_.",
                                    " ",
                                    " .. code-block:: shell-session",
                                    " ",
                                ],
                            },
                            {
                                "header": ["46", "12", "47", "19"],
                                "lines": [
                                    " ",
                                    " You may need to configure a ``.coveragerc`` file. Learn more `here <http://coverage.readthedocs.org/en/latest/config.html>`_. Start with this `generic .coveragerc <https://gist.github.com/codecov-io/bf15bde2c7db1a011b6e>`_ for example.",
                                    " -",
                                ],
                            },
                        ],
                        "stats": {"added": 11, "removed": 4},
                    }
                }
            }
        }
        mock_repo_provider.get_compare.return_value = compare_result
        mock_repo_provider.delete_comment.side_effect = TorngitClientError(
            "code", "response", "message"
        )
        sample_comparison_no_change.pull.commentid = 12
        notifier = CommentNotifier(
            repository=sample_comparison_no_change.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "reach, diff, flags, files, footer",
                "behavior": "default",
                "after_n_builds": 1,
                "require_changes": True,
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        res = await notifier.notify(sample_comparison_no_change)
        assert res.notification_attempted is False
        assert res.notification_successful is None
        assert res.explanation == "changes_required"
        assert res.data_sent is None
        assert res.data_received == {"deleted_comment": False}

    @pytest.mark.asyncio
    async def test_message_hide_details_github(
        self, dbsession, mock_configuration, mock_repo_provider, sample_comparison
    ):
        mock_configuration.params["setup"]["codecov_dashboard_url"] = "test.example.br"
        comparison = sample_comparison
        comparison.repository_service.service = "github"
        pull = comparison.pull
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={"layout": "reach", "hide_comment_details": True},
            notifier_site_settings=True,
            current_yaml={},
        )
        repository = sample_comparison.head.commit.repository
        result = await notifier.build_message(comparison)
        expected_result = [
            f"## [Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=h1) Report",
            f"> Merging [#{pull.pullid}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=desc) ({comparison.head.commit.commitid[:7]}) into [master](test.example.br/gh/{repository.slug}/commit/{sample_comparison.base.commit.commitid}?el=desc) ({sample_comparison.base.commit.commitid[:7]}) will **increase** coverage by `10.00%`.",
            f"> The diff coverage is `66.67%`.",
            f"",
            f"<details><summary>Additional details and impacted files</summary>\n",
            f"",
            f"[![Impacted file tree graph](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/graphs/tree.svg?width=650&height=150&src=pr&token={repository.image_token})](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree)",
            f"",
            f"</details>",
        ]
        li = 0
        for exp, res in zip(expected_result, result):
            li += 1
            print(li)
            assert exp == res
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_message_announcements_only(
        self, dbsession, mock_configuration, mock_repo_provider, sample_comparison
    ):
        mock_configuration.params["setup"]["codecov_dashboard_url"] = "test.example.br"
        comparison = sample_comparison
        comparison.repository_service.service = "github"
        pull = comparison.pull
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={"layout": "announcements"},
            notifier_site_settings=True,
            current_yaml={},
        )
        repository = sample_comparison.head.commit.repository
        result = await notifier.build_message(comparison)
        expected_result = [
            f"## [Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=h1) Report",
            f"> Merging [#{pull.pullid}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=desc) ({comparison.head.commit.commitid[:7]}) into [master](test.example.br/gh/{repository.slug}/commit/{sample_comparison.base.commit.commitid}?el=desc) ({sample_comparison.base.commit.commitid[:7]}) will **increase** coverage by `10.00%`.",
            "> The diff coverage is `66.67%`.",
            "",
            ":mega: message",
            "",
        ]
        for exp, res in zip(expected_result, result):
            if exp == ":mega: message":
                # We might not know the selected message if there are multiple active ones
                assert res.startswith(":mega: ")
                message = res[7:]
                assert message in AnnouncementSectionWriter.current_active_messages
                # We have to change the expected line to pass the global check
                expected_result[4] = f":mega: {message}"
            else:
                assert exp == res
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_message_hide_details_bitbucket(
        self, dbsession, mock_configuration, mock_repo_provider, sample_comparison
    ):
        mock_configuration.params["setup"]["codecov_dashboard_url"] = "test.example.br"
        comparison = sample_comparison
        comparison.repository_service.service = "bitbucket"
        pull = comparison.pull
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={"layout": "reach", "hide_comment_details": True},
            notifier_site_settings=True,
            current_yaml={},
        )
        repository = sample_comparison.head.commit.repository
        result = await notifier.build_message(comparison)
        expected_result = [
            f"## [Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=h1) Report",
            f"> Merging [#{pull.pullid}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=desc) ({comparison.head.commit.commitid[:7]}) into [master](test.example.br/gh/{repository.slug}/commit/{sample_comparison.base.commit.commitid}?el=desc) ({sample_comparison.base.commit.commitid[:7]}) will **increase** coverage by `10.00%`.",
            f"> The diff coverage is `66.67%`.",
            f"",
            f"[![Impacted file tree graph](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/graphs/tree.svg?width=650&height=150&src=pr&token={repository.image_token})](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree)",
            f"",
        ]
        li = 0
        for exp, res in zip(expected_result, result):
            li += 1
            print(li)
            assert exp == res
        assert result == expected_result


class TestFileSectionWriter(object):
    @pytest.mark.asyncio
    async def test_filesection_no_extra_settings(self, sample_comparison, mocker):
        section_writer = FileSectionWriter(
            sample_comparison.head.commit.repository,
            "layout",
            show_complexity=False,
            settings={},
            current_yaml={},
        )
        changes = [
            Change(
                path="file_2.py",
                in_diff=True,
                totals=ReportTotals(
                    files=0,
                    lines=0,
                    hits=-2,
                    misses=1,
                    partials=0,
                    coverage=-23.333330000000004,
                    branches=0,
                    methods=0,
                    messages=0,
                    sessions=0,
                    complexity=0,
                    complexity_total=0,
                    diff=0,
                ),
            ),
            Change(
                path="unrelated.py",
                in_diff=False,
                totals=ReportTotals(
                    files=0,
                    lines=0,
                    hits=-3,
                    misses=2,
                    partials=0,
                    coverage=-43.333330000000004,
                    branches=0,
                    methods=0,
                    messages=0,
                    sessions=0,
                    complexity=0,
                    complexity_total=0,
                    diff=0,
                ),
            ),
            Change(path="added.py", new=True, in_diff=None, old_path=None, totals=None),
        ]
        lines = list(
            await section_writer.write_section(
                sample_comparison,
                {
                    "files": {
                        "file_1.go": {
                            "type": "added",
                            "totals": ReportTotals(
                                lines=3,
                                hits=2,
                                misses=1,
                                coverage=66.66,
                                branches=0,
                                methods=0,
                                messages=0,
                                sessions=0,
                                complexity=0,
                                complexity_total=0,
                                diff=0,
                            ),
                        }
                    }
                },
                changes,
                links={"pull": "pull.link"},
            )
        )
        assert lines == [
            "| [Files](pull.link?src=pr&el=tree) | Coverage Δ | |",
            "|---|---|---|",
            "| [file\\_1.go](pull.link?src=pr&el=tree#diff-ZmlsZV8xLmdv) | `62.50% <66.66%> (+12.50%)` | :arrow_up: |",
            f"",
            "... and [3 files with indirect coverage changes](pull.link/indirect-changes?src=pr&el=tree-more)",
        ]

    @pytest.mark.asyncio
    async def test_file_with_critical(self, sample_comparison, mocker):
        critical_path_report = mocker.MagicMock(
            get_critical_files_filenames=mocker.MagicMock(
                return_value=["file_1.go", "added.py"]
            )
        )
        mocker.patch(
            "services.comparison.overlays.critical_path._load_critical_path_report",
            return_value=critical_path_report,
        )
        section_writer = FileSectionWriter(
            sample_comparison.head.commit.repository,
            "layout",
            show_complexity=False,
            settings={"show_critical_paths": True},
            current_yaml={},
        )
        changes = [
            Change(
                path="file_2.py",
                in_diff=True,
                totals=ReportTotals(
                    files=0,
                    lines=0,
                    hits=-2,
                    misses=1,
                    partials=0,
                    coverage=-23.333330000000004,
                    branches=0,
                    methods=0,
                    messages=0,
                    sessions=0,
                    complexity=0,
                    complexity_total=0,
                    diff=0,
                ),
            ),
            Change(
                path="unrelated.py",
                in_diff=False,
                totals=ReportTotals(
                    files=0,
                    lines=0,
                    hits=-3,
                    misses=2,
                    partials=0,
                    coverage=-43.333330000000004,
                    branches=0,
                    methods=0,
                    messages=0,
                    sessions=0,
                    complexity=0,
                    complexity_total=0,
                    diff=0,
                ),
            ),
            Change(path="added.py", new=True, in_diff=None, old_path=None, totals=None),
        ]
        lines = list(
            await section_writer.write_section(
                sample_comparison,
                {
                    "files": {
                        "file_1.go": {
                            "type": "added",
                            "totals": ReportTotals(
                                lines=3,
                                hits=2,
                                misses=1,
                                coverage=66.66,
                                branches=0,
                                methods=0,
                                messages=0,
                                sessions=0,
                                complexity=0,
                                complexity_total=0,
                                diff=0,
                            ),
                        }
                    }
                },
                changes,
                links={"pull": "pull.link"},
            )
        )
        assert lines == [
            "| [Files](pull.link?src=pr&el=tree) | Coverage Δ | |",
            "|---|---|---|",
            "| [file\\_1.go](pull.link?src=pr&el=tree#diff-ZmlsZV8xLmdv) **Critical** | `62.50% <66.66%> (+12.50%)` | :arrow_up: |",
            "",
            "... and [3 files with indirect coverage changes](pull.link/indirect-changes?src=pr&el=tree-more)",
        ]

    @pytest.mark.asyncio
    async def test_filesection_hide_project_cov(self, sample_comparison, mocker):
        section_writer = NewFilesSectionWriter(
            sample_comparison.head.commit.repository,
            "layout",
            show_complexity=False,
            settings={"hide_project_coverage": True},
            current_yaml={},
        )
        changes = [
            Change(
                path="unrelated.py",
                in_diff=False,
                totals=ReportTotals(
                    files=0,
                    lines=0,
                    hits=-3,
                    misses=2,
                    partials=0,
                    coverage=-43.333330000000004,
                    branches=0,
                    methods=0,
                    messages=0,
                    sessions=0,
                    complexity=0,
                    complexity_total=0,
                    diff=0,
                ),
            ),
            Change(path="added.py", new=True, in_diff=None, old_path=None, totals=None),
        ]
        lines = list(
            await section_writer.write_section(
                sample_comparison,
                {
                    "files": {
                        "file_1.go": {
                            "type": "added",
                            "totals": ReportTotals(
                                lines=3,
                                hits=2,
                                misses=1,
                                coverage=66.66,
                                branches=0,
                                methods=0,
                                messages=0,
                                sessions=0,
                                complexity=0,
                                complexity_total=0,
                                diff=0,
                            ),
                        },
                        "file_2.py": {
                            "type": "added",
                            "totals": ReportTotals(
                                lines=3,
                                hits=-2,
                                misses=2,
                                partials=3,
                                coverage=-23.333330000000004,
                                branches=0,
                                methods=0,
                                messages=0,
                                sessions=0,
                                complexity=0,
                                complexity_total=0,
                                diff=0,
                            ),
                        },
                    }
                },
                changes,
                links={"pull": "pull.link"},
            )
        )
        assert lines == [
            "| [Files](pull.link?src=pr&el=tree) | Patch % | Lines |",
            "|---|---|---|",
            "| [file\\_2.py](pull.link?src=pr&el=tree#diff-ZmlsZV8yLnB5) | -23.33% | [2 Missing and 3 partials :warning: ](pull.link?src=pr&el=tree) |",
            "| [file\\_1.go](pull.link?src=pr&el=tree#diff-ZmlsZV8xLmdv) | 66.66% | [1 Missing :warning: ](pull.link?src=pr&el=tree) |",
        ]

    @pytest.mark.asyncio
    async def test_filesection_hide_project_cov_with_changed_files_but_no_missing_lines(
        self, sample_comparison, mocker
    ):
        section_writer = NewFilesSectionWriter(
            sample_comparison.head.commit.repository,
            "layout",
            show_complexity=False,
            settings={"hide_project_coverage": True},
            current_yaml={},
        )
        changes = [
            Change(
                path="unrelated.py",
                in_diff=False,
                totals=ReportTotals(
                    files=0,
                    lines=0,
                    hits=-3,
                    misses=2,
                    partials=0,
                    coverage=-43.333330000000004,
                    branches=0,
                    methods=0,
                    messages=0,
                    sessions=0,
                    complexity=0,
                    complexity_total=0,
                    diff=0,
                ),
            ),
            Change(path="added.py", new=True, in_diff=None, old_path=None, totals=None),
        ]
        lines = list(
            await section_writer.write_section(
                sample_comparison,
                {
                    "files": {
                        "file_1.go": {
                            "type": "added",
                            "totals": ReportTotals(
                                lines=3,
                                hits=3,
                                misses=0,
                                coverage=100.00,
                                branches=0,
                                methods=0,
                                messages=0,
                                sessions=0,
                                complexity=0,
                                complexity_total=0,
                                diff=0,
                            ),
                        },
                        "file_2.py": {
                            "type": "added",
                            "totals": ReportTotals(
                                lines=3,
                                hits=3,
                                misses=0,
                                partials=0,
                                coverage=-100.00,
                                branches=0,
                                methods=0,
                                messages=0,
                                sessions=0,
                                complexity=0,
                                complexity_total=0,
                                diff=0,
                            ),
                        },
                    }
                },
                changes,
                links={"pull": "pull.link"},
            )
        )
        assert lines == []

    @pytest.mark.asyncio
    async def test_filesection_hide_project_cov_no_files_changed(
        self, sample_comparison, mocker
    ):
        section_writer = NewFilesSectionWriter(
            sample_comparison.head.commit.repository,
            "layout",
            show_complexity=False,
            settings={"hide_project_coverage": True},
            current_yaml={},
        )
        changes = [
            Change(
                path="unrelated.py",
                in_diff=False,
                totals=ReportTotals(
                    files=0,
                    lines=0,
                    hits=-3,
                    misses=2,
                    partials=0,
                    coverage=-43.333330000000004,
                    branches=0,
                    methods=0,
                    messages=0,
                    sessions=0,
                    complexity=0,
                    complexity_total=0,
                    diff=0,
                ),
            ),
            Change(path="added.py", new=True, in_diff=None, old_path=None, totals=None),
        ]
        lines = list(
            await section_writer.write_section(
                sample_comparison,
                {"files": {}},
                changes,
                links={"pull": "pull.link"},
            )
        )
        assert lines == []


class TestImpactedEndpointWriter(object):
    @pytest.mark.asyncio
    async def test_impacted_endpoints_table(
        self, sample_comparison, mocker, mock_repo_provider
    ):
        mock_repo_provider.get_compare.return_value = {
            "diff": {
                "files": {
                    "README.md": {
                        "type": "modified",
                        "before": None,
                        "segments": [
                            {
                                "header": ["5", "8", "5", "9"],
                                "lines": [
                                    " Overview",
                                    " --------",
                                    " ",
                                    "-Main website: `Codecov <https://codecov.io/>`_.",
                                    "-Main website: `Codecov <https://codecov.io/>`_.",
                                    "+",
                                    "+website: `Codecov <https://codecov.io/>`_.",
                                    "+website: `Codecov <https://codecov.io/>`_.",
                                    " ",
                                    " .. code-block:: shell-session",
                                    " ",
                                ],
                            },
                            {
                                "header": ["46", "12", "47", "19"],
                                "lines": [
                                    " ",
                                    " You may need to configure a ``.coveragerc`` file. Learn more `here <http://coverage.readthedocs.org/en/latest/config.html>`_. Start with this `generic .coveragerc <https://gist.github.com/codecov-io/bf15bde2c7db1a011b6e>`_ for example.",
                                    " -",
                                ],
                            },
                        ],
                        "stats": {"added": 11, "removed": 4},
                    }
                }
            }
        }
        mocker.patch.object(
            CriticalPathOverlay,
            "full_analyzer",
            new_callable=mocker.PropertyMock,
            return_value=mocker.MagicMock(
                find_impacted_endpoints=mocker.MagicMock(
                    return_value=[
                        {"group_name": "banana"},
                        {"group_name": "GET /apple"},
                    ]
                )
            ),
        )
        section_writer = ImpactedEntrypointsSectionWriter(
            sample_comparison.head.commit.repository,
            "layout",
            show_complexity=False,
            settings={},
            current_yaml={},
        )
        lines = list(
            await section_writer.write_section(
                sample_comparison,
                {
                    "files": {
                        "file_1.go": {
                            "type": "added",
                            "totals": ReportTotals(
                                lines=3,
                                hits=2,
                                misses=1,
                                coverage=66.66,
                                branches=0,
                                methods=0,
                                messages=0,
                                sessions=0,
                                complexity=0,
                                complexity_total=0,
                                diff=0,
                            ),
                        }
                    }
                },
                [],
                links={"pull": "pull.link"},
            )
        )
        assert lines == ["| Related Entrypoints |", "|---|", "|banana|", "|GET /apple|"]

    @pytest.mark.asyncio
    async def test_impacted_endpoints_table_empty_list_result(
        self, sample_comparison, mocker, mock_repo_provider
    ):
        mocker.patch.object(
            CriticalPathOverlay,
            "full_analyzer",
            new_callable=mocker.PropertyMock,
            return_value=mocker.MagicMock(
                find_impacted_endpoints=mocker.MagicMock(return_value=[])
            ),
        )
        section_writer = ImpactedEntrypointsSectionWriter(
            sample_comparison.head.commit.repository,
            "layout",
            show_complexity=False,
            settings={},
            current_yaml={},
        )
        lines = list(
            await section_writer.write_section(
                sample_comparison,
                {
                    "files": {
                        "file_1.go": {
                            "type": "added",
                            "totals": ReportTotals(
                                lines=3,
                                hits=2,
                                misses=1,
                                coverage=66.66,
                                branches=0,
                                methods=0,
                                messages=0,
                                sessions=0,
                                complexity=0,
                                complexity_total=0,
                                diff=0,
                            ),
                        }
                    }
                },
                [],
                links={"pull": "pull.link"},
            )
        )
        assert lines == [
            "This change has been scanned for critical changes. [Learn more](https://docs.codecov.com/docs/impact-analysis)"
        ]

    @pytest.mark.asyncio
    async def test_impacted_endpoints_table_none_result(
        self, sample_comparison, mocker, mock_repo_provider
    ):
        mocker.patch.object(
            CriticalPathOverlay,
            "full_analyzer",
            new_callable=mocker.PropertyMock,
            return_value=mocker.MagicMock(
                find_impacted_endpoints=mocker.MagicMock(return_value=None)
            ),
        )
        section_writer = ImpactedEntrypointsSectionWriter(
            sample_comparison.head.commit.repository,
            "layout",
            show_complexity=False,
            settings={},
            current_yaml={},
        )
        lines = list(
            await section_writer.write_section(
                sample_comparison,
                {
                    "files": {
                        "file_1.go": {
                            "type": "added",
                            "totals": ReportTotals(
                                lines=3,
                                hits=2,
                                misses=1,
                                coverage=66.66,
                                branches=0,
                                methods=0,
                                messages=0,
                                sessions=0,
                                complexity=0,
                                complexity_total=0,
                                diff=0,
                            ),
                        }
                    }
                },
                [],
                links={"pull": "pull.link"},
            )
        )
        assert lines == []


class TestNewHeaderSectionWriter(object):
    @pytest.mark.asyncio
    async def test_new_header_section_writer(self, mocker, sample_comparison):
        writer = NewHeaderSectionWriter(
            mocker.MagicMock(),
            mocker.MagicMock(),
            show_complexity=mocker.MagicMock(),
            settings={},
            current_yaml=mocker.MagicMock(),
        )
        mocker.patch(
            "services.notification.notifiers.mixins.message.sections.round_number",
            return_value=Decimal(0),
        )
        res = list(
            await writer.write_section(
                sample_comparison,
                None,
                None,
                links={"pull": "urlurl", "base": "urlurl"},
            )
        )
        print(res)
        assert res == [
            "All modified and coverable lines are covered by tests :white_check_mark:",
            f"> Comparison is base [(`{sample_comparison.base.commit.commitid[:7]}`)](urlurl?el=desc) 0% compared to head [(`{sample_comparison.head.commit.commitid[:7]}`)](urlurl?src=pr&el=desc) 0%.",
        ]

    @pytest.mark.asyncio
    async def test_new_header_section_writer_with_behind_by(
        self, mocker, sample_comparison
    ):
        writer = NewHeaderSectionWriter(
            mocker.MagicMock(),
            mocker.MagicMock(),
            show_complexity=mocker.MagicMock(),
            settings={},
            current_yaml=mocker.MagicMock(),
        )
        mocker.patch(
            "services.notification.notifiers.mixins.message.sections.round_number",
            return_value=Decimal(0),
        )
        res = list(
            await writer.write_section(
                sample_comparison,
                None,
                None,
                links={"pull": "urlurl", "base": "urlurl"},
                behind_by=3,
            )
        )
        print(res)
        assert res == [
            "All modified and coverable lines are covered by tests :white_check_mark:",
            f"> Comparison is base [(`{sample_comparison.base.commit.commitid[:7]}`)](urlurl?el=desc) 0% compared to head [(`{sample_comparison.head.commit.commitid[:7]}`)](urlurl?src=pr&el=desc) 0%.",
            "> Report is 3 commits behind head on master.",
        ]

    @pytest.mark.asyncio
    async def test_new_header_section_writer_no_project_coverage(
        self, mocker, sample_comparison
    ):
        writer = NewHeaderSectionWriter(
            mocker.MagicMock(),
            mocker.MagicMock(),
            show_complexity=mocker.MagicMock(),
            settings={"hide_project_coverage": True},
            current_yaml=mocker.MagicMock(),
        )
        mocker.patch(
            "services.notification.notifiers.mixins.message.sections.round_number",
            return_value=Decimal(0),
        )
        res = list(
            await writer.write_section(
                sample_comparison,
                None,
                None,
                links={"pull": "urlurl", "base": "urlurl"},
            )
        )
        assert res == [
            "All modified and coverable lines are covered by tests :white_check_mark:",
        ]


class TestAnnouncementsSectionWriter(object):
    @pytest.mark.asyncio
    async def test_announcement_section_writer(self, mocker):
        writer = AnnouncementSectionWriter(
            mocker.MagicMock(),
            mocker.MagicMock(),
            mocker.MagicMock(),
            mocker.MagicMock(),
            mocker.MagicMock(),
        )
        res = list(await writer.write_section(mocker.MagicMock()))
        assert len(res) == 1
        line = res[0]
        assert line.startswith(":mega: ")
        message = line[7:]
        assert message in AnnouncementSectionWriter.current_active_messages

    @pytest.mark.asyncio
    async def test_announcement_section_writer_ats(
        self, mocker, create_sample_comparison
    ):
        comparison = create_sample_comparison()
        current_yaml = UserYaml({})

        writer = AnnouncementSectionWriter(
            repository=comparison.head.commit.repository,
            layout=mocker.MagicMock(),
            show_complexity=mocker.MagicMock(),
            settings=mocker.MagicMock(),
            current_yaml=current_yaml,
        )
        writer.repository.language = "python"
        comparison.head.report._chunks = ["xx"] * 80_000_000

        res = list(await writer.write_section(comparison))
        assert len(res) == 1
        line = res[0]
        assert line.startswith(":mega: ")
        assert "smart automated test selection" in line


class TestNewFooterSectionWriter(object):
    @pytest.mark.asyncio
    async def test_footer_section_writer_in_github(self, mocker):
        writer = NewFooterSectionWriter(
            mocker.MagicMock(),
            mocker.MagicMock(),
            mocker.MagicMock(),
            settings={},
            current_yaml=mocker.MagicMock(),
        )
        mock_comparison = mocker.MagicMock()
        mock_comparison.repository_service.service = "github"
        res = list(
            await writer.write_section(
                mock_comparison, {}, [], links={"pull": "pull.link"}
            )
        )
        assert res == [
            "",
            "[:umbrella: View full report in Codecov by Sentry](pull.link?src=pr&el=continue).   ",
            ":loudspeaker: Have feedback on the report? [Share it here](https://about.codecov.io/codecov-pr-comment-feedback/).",
        ]

    @pytest.mark.asyncio
    async def test_footer_section_writer_in_gitlab(self, mocker):
        writer = NewFooterSectionWriter(
            mocker.MagicMock(),
            mocker.MagicMock(),
            mocker.MagicMock(),
            settings={},
            current_yaml=mocker.MagicMock(),
        )
        mock_comparison = mocker.MagicMock()
        mock_comparison.repository_service.service = "gitlab"
        res = list(
            await writer.write_section(
                mock_comparison, {}, [], links={"pull": "pull.link"}
            )
        )
        assert res == [
            "",
            "[:umbrella: View full report in Codecov by Sentry](pull.link?src=pr&el=continue).   ",
            ":loudspeaker: Have feedback on the report? [Share it here](https://gitlab.com/codecov-open-source/codecov-user-feedback/-/issues/4).",
        ]

    @pytest.mark.asyncio
    async def test_footer_section_writer_in_bitbucket(self, mocker):
        writer = NewFooterSectionWriter(
            mocker.MagicMock(),
            mocker.MagicMock(),
            mocker.MagicMock(),
            settings={},
            current_yaml=mocker.MagicMock(),
        )
        mock_comparison = mocker.MagicMock()
        mock_comparison.repository_service.service = "bitbucket"
        res = list(
            await writer.write_section(
                mock_comparison, {}, [], links={"pull": "pull.link"}
            )
        )
        assert res == [
            "",
            "[:umbrella: View full report in Codecov by Sentry](pull.link?src=pr&el=continue).   ",
            ":loudspeaker: Have feedback on the report? [Share it here](https://gitlab.com/codecov-open-source/codecov-user-feedback/-/issues/4).",
        ]

    @pytest.mark.asyncio
    async def test_footer_section_writer_with_project_cov_hidden(self, mocker):
        writer = NewFooterSectionWriter(
            mocker.MagicMock(),
            mocker.MagicMock(),
            mocker.MagicMock(),
            settings={
                "layout": "newheader, files, newfooter",
                "hide_project_coverage": True,
            },
            current_yaml={},
        )
        mock_comparison = mocker.MagicMock()
        mock_comparison.repository_service.service = "bitbucket"
        res = list(
            await writer.write_section(
                mock_comparison, {}, [], links={"pull": "pull.link"}
            )
        )
        assert res == [
            "",
            ":loudspeaker: Thoughts on this report? [Let us know!](https://about.codecov.io/pull-request-comment-report/)",
        ]


@pytest.mark.usefixtures("is_not_first_pull")
class TestCommentNotifierInNewLayout(object):
    @pytest.mark.asyncio
    async def test_create_message_files_section_with_critical_files_new_layout(
        self,
        dbsession,
        mock_configuration,
        mock_repo_provider,
        sample_comparison,
        mocker,
    ):
        comparison = sample_comparison
        mocker.patch.object(
            comparison,
            "get_diff",
            return_value={
                "files": {
                    "file_1.go": {
                        "type": "modified",
                        "before": None,
                        "segments": [
                            {
                                "header": ["105", "8", "105", "9"],
                                "lines": [
                                    " Overview",
                                    " --------",
                                    " ",
                                    "-Main website: `Codecov <https://codecov.io/>`_.",
                                    "-Main website: `Codecov <https://codecov.io/>`_.",
                                    "+",
                                    "+website: `Codecov <https://codecov.io/>`_.",
                                    "+website: `Codecov <https://codecov.io/>`_.",
                                    " ",
                                    " .. code-block:: shell-session",
                                    " ",
                                ],
                            },
                            {
                                "header": ["1046", "12", "1047", "19"],
                                "lines": [
                                    " ",
                                    " You may need to configure a ``.coveragerc`` file. Learn more",
                                    " ",
                                    "-We highly suggest adding `source` to your ``.coveragerc``",
                                    "+We highly suggest adding ``source`` to your ``.coveragerc`",
                                    " ",
                                    " .. code-block:: ini",
                                    " ",
                                    "    [run]",
                                    "    source=your_package_name",
                                    "+   ",
                                    "+If there are multiple sources, you instead should add ``include",
                                    "+",
                                    "+.. code-block:: ini",
                                    "+",
                                    "+   [run]",
                                    "+   include=your_package_name/*",
                                    " ",
                                    " unittests",
                                    " ---------",
                                ],
                            },
                            {
                                "header": ["10150", "5", "10158", "4"],
                                "lines": [
                                    " * Twitter: `@codecov <https://twitter.com/codecov>`_.",
                                    " * Email: `hello@codecov.io <hello@codecov.io>`_.",
                                    " ",
                                    "-We are happy to help if you have any questions. ",
                                    "-",
                                    "+We are happy to help if you have any questions. .",
                                ],
                            },
                        ],
                        "stats": {"added": 11, "removed": 4},
                    },
                    "file_2.py": {
                        "type": "modified",
                        "before": None,
                        "segments": [
                            {
                                "header": ["10", "8", "10", "9"],
                                "lines": [
                                    " Overview",
                                    " --------",
                                    " ",
                                    "-Main website: `Codecov <https://codecov.io/>`_.",
                                    "-Main website: `Codecov <https://codecov.io/>`_.",
                                    "+",
                                    "+website: `Codecov <https://codecov.io/>`_.",
                                    "+website: `Codecov <https://codecov.io/>`_.",
                                    " ",
                                    " .. code-block:: shell-session",
                                    " ",
                                ],
                            },
                            {
                                "header": ["50", "12", "51", "19"],
                                "lines": [
                                    " ",
                                    " You may need to configure a ``.coveragerc`` file. Learn more `here <http://coverage.readthedocs.org/en/latest/config.html>`_. Start with this `generic .coveragerc <https://gist.github.com/codecov-io/bf15bde2c7db1a011b6e>`_ for example.",
                                    " ",
                                    "-We highly suggest adding `source` to your ``.coveragerc`` which solves a number of issues collecting coverage.",
                                    "+We highly suggest adding ``source`` to your ``.coveragerc``, which solves a number of issues collecting coverage.",
                                    " ",
                                    " .. code-block:: ini",
                                    " ",
                                    "    [run]",
                                    "    source=your_package_name",
                                    "+   ",
                                    "+If there are multiple sources, you instead should add ``include`` to your ``.coveragerc``",
                                    "+",
                                    "+.. code-block:: ini",
                                    "+",
                                    "+   [run]",
                                    "+   include=your_package_name/*",
                                    " ",
                                    " unittests",
                                    " ---------",
                                ],
                            },
                        ],
                        "stats": {"added": 11, "removed": 4},
                    },
                }
            },
        )
        mocked_search_files_for_critical_changes = mocker.patch.object(
            CriticalPathOverlay,
            "search_files_for_critical_changes",
            return_value=["file_2.py"],
        )
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "newheader,files,betaprofiling",
                "show_critical_paths": True,
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        pull = comparison.pull
        repository = sample_comparison.head.commit.repository
        expected_result = [
            f"## [Codecov](https://app.codecov.io/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=h1) Report",
            f"All modified and coverable lines are covered by tests :white_check_mark:",
            f"> Comparison is base [(`{comparison.base.commit.commitid[:7]}`)](https://app.codecov.io/gh/{repository.slug}/commit/{comparison.base.commit.commitid}?el=desc) 50.00% compared to head [(`{comparison.head.commit.commitid[:7]}`)](https://app.codecov.io/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=desc) 60.00%.",
            "",
            "Changes have been made to critical files, which contain lines commonly executed in production. [Learn more](https://docs.codecov.com/docs/impact-analysis)",
            "",
            f"| [Files](https://app.codecov.io/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree) | Coverage Δ | Complexity Δ | |",
            f"|---|---|---|---|",
            f"| [file\\_1.go](https://app.codecov.io/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree#diff-ZmlsZV8xLmdv) | `62.50% <ø> (+12.50%)` | `10.00 <0.00> (-1.00)` | :arrow_up: |",
            f"| [file\\_2.py](https://app.codecov.io/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree#diff-ZmlsZV8yLnB5) **Critical** | `50.00% <ø> (ø)` | `0.00 <0.00> (ø)` | |",
            f"",
            "",
        ]
        res = await notifier.build_message(comparison)
        assert expected_result == res
        mocked_search_files_for_critical_changes.assert_called_with(
            {"file_2.py", "file_1.go"}
        )
        assert mocked_search_files_for_critical_changes.call_count == 2

    @pytest.mark.asyncio
    async def test_build_message_no_base_commit_new_layout(
        self,
        dbsession,
        mock_configuration,
        mock_repo_provider,
        sample_comparison_without_base_with_pull,
    ):
        mock_configuration.params["setup"]["codecov_dashboard_url"] = "test.example.br"
        comparison = sample_comparison_without_base_with_pull
        comparison.repository_service.service = "github"
        pull = comparison.pull
        notifier = CommentNotifier(
            repository=comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "newheader, reach, diff, flags, files, newfooter"
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        repository = comparison.head.commit.repository
        result = await notifier.build_message(comparison)
        expected_result = [
            f"## [Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=h1) Report",
            f"All modified and coverable lines are covered by tests :white_check_mark:",
            f"> :exclamation: No coverage uploaded for pull request base (`master@cdf9aa4`). [Click here to learn what that means](https://docs.codecov.io/docs/error-reference#section-missing-base-commit).",
            f"",
            f"[![Impacted file tree graph](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/graphs/tree.svg?width=650&height=150&src=pr&token={repository.image_token})](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree)",
            f"",
            f"```diff",
            f"@@            Coverage Diff            @@",
            f"##             master      #{pull.pullid}   +/-   ##",
            f"=========================================",
            f"  Coverage          ?   60.00%           ",
            f"  Complexity        ?       10           ",
            f"=========================================",
            f"  Files             ?        2           ",
            f"  Lines             ?       10           ",
            f"  Branches          ?        1           ",
            f"=========================================",
            f"  Hits              ?        6           ",
            f"  Misses            ?        3           ",
            f"  Partials          ?        1           ",
            f"```",
            f"",
            f"| [Flag](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flags) | Coverage Δ | Complexity Δ | |",
            f"|---|---|---|---|",
            f"| [unit](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `100.00% <0.00%> (?)` | `0.00% <0.00%> (?%)` | |",
            f"",
            f"Flags with carried forward coverage won't be shown. [Click here](https://docs.codecov.io/docs/carryforward-flags#carryforward-flags-in-the-pull-request-comment) to find out more.",
            f"",
            f"",
            f"",
            f"[:umbrella: View full report in Codecov by Sentry](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=continue).   ",
            f":loudspeaker: Have feedback on the report? [Share it here](https://about.codecov.io/codecov-pr-comment-feedback/).",
            f"",
        ]
        for exp, res in zip(expected_result, result):
            assert exp == res
            print(res)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_build_message_no_base_report_new_layout(
        self,
        dbsession,
        mock_configuration,
        mock_repo_provider,
        sample_comparison_without_base_report,
    ):
        mock_configuration.params["setup"]["codecov_dashboard_url"] = "test.example.br"
        comparison = sample_comparison_without_base_report
        comparison.repository_service.service = "github"
        pull = comparison.pull
        notifier = CommentNotifier(
            repository=comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "newheader, reach, diff, flags, files, newfooter",
                "hide_comment_details": True,
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        repository = comparison.head.commit.repository
        result = await notifier.build_message(comparison)
        expected_result = [
            f"## [Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=h1) Report",
            f"Attention: `1 lines` in your changes are missing coverage. Please review.",
            f"> :exclamation: No coverage uploaded for pull request base (`master@{comparison.base.commit.commitid[:7]}`). [Click here to learn what that means](https://docs.codecov.io/docs/error-reference#section-missing-base-commit).",
            f"",
            f"<details><summary>Additional details and impacted files</summary>\n",
            f"",
            f"[![Impacted file tree graph](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/graphs/tree.svg?width=650&height=150&src=pr&token={repository.image_token})](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree)",
            f"",
            f"```diff",
            f"@@            Coverage Diff            @@",
            f"##             master      #{pull.pullid}   +/-   ##",
            f"=========================================",
            f"  Coverage          ?   60.00%           ",
            f"  Complexity        ?       10           ",
            f"=========================================",
            f"  Files             ?        2           ",
            f"  Lines             ?       10           ",
            f"  Branches          ?        1           ",
            f"=========================================",
            f"  Hits              ?        6           ",
            f"  Misses            ?        3           ",
            f"  Partials          ?        1           ",
            f"```",
            f"",
            f"| [Flag](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flags) | Coverage Δ | Complexity Δ | |",
            f"|---|---|---|---|",
            f"| [unit](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `100.00% <100.00%> (?)` | `0.00 <0.00> (?)` | |",
            f"",
            f"Flags with carried forward coverage won't be shown. [Click here](https://docs.codecov.io/docs/carryforward-flags#carryforward-flags-in-the-pull-request-comment) to find out more.",
            f"",
            f"| [Files](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree) | Coverage Δ | Complexity Δ | |",
            f"|---|---|---|---|",
            f"| [file\_1.go](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree#diff-ZmlsZV8xLmdv) | `62.50% <66.67%> (ø)` | `10.00 <0.00> (?)` | |",
            f"",
            f"</details>",
            f"",
            f"[:umbrella: View full report in Codecov by Sentry](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=continue).   ",
            f":loudspeaker: Have feedback on the report? [Share it here](https://about.codecov.io/codecov-pr-comment-feedback/).",
            f"",
        ]
        for exp, res in zip(expected_result, result):
            assert exp == res
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_build_message_no_project_coverage(
        self,
        dbsession,
        mock_configuration,
        mock_repo_provider,
        sample_comparison,
    ):
        mock_configuration.params["setup"]["codecov_dashboard_url"] = "test.example.br"
        comparison = sample_comparison
        comparison.repository_service.service = "github"
        pull = comparison.pull
        notifier = CommentNotifier(
            repository=comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "newheader, newfiles, newfooter",
                "hide_project_coverage": True,
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        repository = comparison.head.commit.repository
        result = await notifier.build_message(comparison)
        pull_url = f"test.example.br/gh/{repository.slug}/pull/{pull.pullid}"
        expected_result = [
            f"## [Codecov]({pull_url}?src=pr&el=h1) Report",
            f"Attention: `1 lines` in your changes are missing coverage. Please review.",
            f"",
            f"| [Files]({pull_url}?src=pr&el=tree) | Patch % | Lines |",
            f"|---|---|---|",
            f"| [file\\_1.go]({pull_url}?src=pr&el=tree#diff-ZmlsZV8xLmdv) | 66.67% | [1 Missing :warning: ]({pull_url}?src=pr&el=tree) |",
            f"",
            f"",
            f":loudspeaker: Thoughts on this report? [Let us know!](https://about.codecov.io/pull-request-comment-report/)",
            f"",
        ]
        for exp, res in zip(expected_result, result):
            assert exp == res
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_build_message_no_project_coverage_condensed_yaml_configs(
        self,
        dbsession,
        mock_configuration,
        mock_repo_provider,
        sample_comparison,
    ):
        mock_configuration.params["setup"]["codecov_dashboard_url"] = "test.example.br"
        comparison = sample_comparison
        comparison.repository_service.service = "github"
        pull = comparison.pull
        notifier = CommentNotifier(
            repository=comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "condensed_header, condensed_files, condensed_footer",
                "hide_project_coverage": True,
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        repository = comparison.head.commit.repository
        result = await notifier.build_message(comparison)
        pull_url = f"test.example.br/gh/{repository.slug}/pull/{pull.pullid}"
        expected_result = [
            f"## [Codecov]({pull_url}?src=pr&el=h1) Report",
            f"Attention: `1 lines` in your changes are missing coverage. Please review.",
            f"",
            f"| [Files]({pull_url}?src=pr&el=tree) | Patch % | Lines |",
            f"|---|---|---|",
            f"| [file\\_1.go]({pull_url}?src=pr&el=tree#diff-ZmlsZV8xLmdv) | 66.67% | [1 Missing :warning: ]({pull_url}?src=pr&el=tree) |",
            f"",
            f"",
            f":loudspeaker: Thoughts on this report? [Let us know!](https://about.codecov.io/pull-request-comment-report/)",
            f"",
        ]
        for exp, res in zip(expected_result, result):
            assert exp == res
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_build_message_head_and_pull_head_differ_new_layout(
        self,
        dbsession,
        mock_configuration,
        mock_repo_provider,
        sample_comparison_head_and_pull_head_differ,
    ):
        mock_configuration.params["setup"]["codecov_dashboard_url"] = "test.example.br"
        comparison = sample_comparison_head_and_pull_head_differ
        comparison.repository_service.service = "github"
        pull = comparison.pull
        notifier = CommentNotifier(
            repository=comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "newheader, reach, diff, flags, newfooter",
                "hide_comment_details": True,
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        repository = comparison.head.commit.repository
        result = await notifier.build_message(comparison)
        expected_result = [
            f"## [Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=h1) Report",
            f"Attention: `1 lines` in your changes are missing coverage. Please review.",
            f"> Comparison is base [(`{comparison.base.commit.commitid[:7]}`)](test.example.br/gh/{repository.slug}/commit/{comparison.base.commit.commitid}?el=desc) 50.00% compared to head [(`{comparison.head.commit.commitid[:7]}`)](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=desc) 60.00%.",
            f"",
            f"> :exclamation: Current head {comparison.head.commit.commitid[:7]} differs from pull request most recent head {comparison.enriched_pull.provider_pull['head']['commitid'][:7]}. Consider uploading reports for the commit {comparison.enriched_pull.provider_pull['head']['commitid'][:7]} to get more accurate results",
            f"",
            f"<details><summary>Additional details and impacted files</summary>\n",
            f"",
            f"[![Impacted file tree graph](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/graphs/tree.svg?width=650&height=150&src=pr&token={repository.image_token})](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree)",
            f"",
            f"```diff",
            f"@@              Coverage Diff              @@",
            f"##             master      #{pull.pullid}       +/-   ##",
            f"=============================================",
            f"+ Coverage     50.00%   60.00%   +10.00%     ",
            f"+ Complexity       11       10        -1     ",
            f"=============================================",
            f"  Files             2        2               ",
            f"  Lines             6       10        +4     ",
            f"  Branches          0        1        +1     ",
            f"=============================================",
            f"+ Hits              3        6        +3     ",
            f"  Misses            3        3               ",
            f"- Partials          0        1        +1     ",
            f"```",
            f"",
            f"| [Flag](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flags) | Coverage Δ | Complexity Δ | |",
            f"|---|---|---|---|",
            f"| [integration](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `?` | `?` | |",
            f"| [unit](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `100.00% <100.00%> (?)` | `0.00 <0.00> (?)` | |",
            f"",
            f"Flags with carried forward coverage won't be shown. [Click here](https://docs.codecov.io/docs/carryforward-flags#carryforward-flags-in-the-pull-request-comment) to find out more.",
            f"",
            f"</details>",
            f"",
            f"[:umbrella: View full report in Codecov by Sentry](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=continue).   ",
            f":loudspeaker: Have feedback on the report? [Share it here](https://about.codecov.io/codecov-pr-comment-feedback/).",
            f"",
        ]
        for exp, res in zip(expected_result, result):
            assert exp == res
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_build_message_head_and_pull_head_differ_with_components(
        self,
        dbsession,
        mock_configuration,
        mock_repo_provider,
        sample_comparison_head_and_pull_head_differ,
    ):
        mock_configuration.params["setup"]["codecov_dashboard_url"] = "test.example.br"
        comparison = sample_comparison_head_and_pull_head_differ
        comparison.repository_service.service = "github"
        pull = comparison.pull
        notifier = CommentNotifier(
            repository=comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "newheader, reach, diff, flags, components, newfooter",
                "hide_comment_details": True,
            },
            notifier_site_settings=True,
            current_yaml={
                "component_management": {
                    "individual_components": [
                        {"component_id": "go_files", "paths": [r".*\.go"]},
                        {"component_id": "unit_flags", "flag_regexes": [r"unit.*"]},
                    ]
                }
            },
        )
        repository = comparison.head.commit.repository
        result = await notifier.build_message(comparison)
        expected_result = [
            f"## [Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=h1) Report",
            f"Attention: `1 lines` in your changes are missing coverage. Please review.",
            f"> Comparison is base [(`{comparison.base.commit.commitid[:7]}`)](test.example.br/gh/{repository.slug}/commit/{comparison.base.commit.commitid}?el=desc) 50.00% compared to head [(`{comparison.head.commit.commitid[:7]}`)](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=desc) 60.00%.",
            f"",
            f"> :exclamation: Current head {comparison.head.commit.commitid[:7]} differs from pull request most recent head {comparison.enriched_pull.provider_pull['head']['commitid'][:7]}. Consider uploading reports for the commit {comparison.enriched_pull.provider_pull['head']['commitid'][:7]} to get more accurate results",
            f"",
            f"<details><summary>Additional details and impacted files</summary>\n",
            f"",
            f"[![Impacted file tree graph](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/graphs/tree.svg?width=650&height=150&src=pr&token={repository.image_token})](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree)",
            f"",
            f"```diff",
            f"@@              Coverage Diff              @@",
            f"##             master      #{pull.pullid}       +/-   ##",
            f"=============================================",
            f"+ Coverage     50.00%   60.00%   +10.00%     ",
            f"+ Complexity       11       10        -1     ",
            f"=============================================",
            f"  Files             2        2               ",
            f"  Lines             6       10        +4     ",
            f"  Branches          0        1        +1     ",
            f"=============================================",
            f"+ Hits              3        6        +3     ",
            f"  Misses            3        3               ",
            f"- Partials          0        1        +1     ",
            f"```",
            f"",
            f"| [Flag](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flags) | Coverage Δ | Complexity Δ | |",
            f"|---|---|---|---|",
            f"| [integration](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `?` | `?` | |",
            f"| [unit](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `100.00% <100.00%> (?)` | `0.00 <0.00> (?)` | |",
            f"",
            f"Flags with carried forward coverage won't be shown. [Click here](https://docs.codecov.io/docs/carryforward-flags#carryforward-flags-in-the-pull-request-comment) to find out more.",
            f"",
            f"| [Components](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/components?src=pr&el=components) | Coverage Δ | |",
            f"|---|---|---|",
            f"| [go_files](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/components?src=pr&el=component) | `62.50% <66.67%> (+12.50%)` | :arrow_up: |",
            f"| [unit_flags](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/components?src=pr&el=component) | `100.00% <100.00%> (∅)` | |",
            f"",
            f"</details>",
            f"",
            f"[:umbrella: View full report in Codecov by Sentry](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=continue).   ",
            f":loudspeaker: Have feedback on the report? [Share it here](https://about.codecov.io/codecov-pr-comment-feedback/).",
            f"",
        ]
        for exp, res in zip(expected_result, result):
            assert exp == res
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_build_message_no_patch_or_proj_change(
        self,
        dbsession,
        mock_configuration,
        mock_repo_provider,
        sample_comparison_coverage_carriedforward,
    ):
        mock_configuration.params["setup"]["codecov_dashboard_url"] = "test.example.br"
        comparison = sample_comparison_coverage_carriedforward
        pull = comparison.pull
        notifier = CommentNotifier(
            repository=comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={
                "layout": "newheader, reach, diff, flags, files, footer",
            },
            notifier_site_settings=True,
            current_yaml={},
        )
        repository = comparison.head.commit.repository
        result = await notifier.build_message(comparison)
        expected_result = [
            f"## [Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=h1) Report",
            f"All modified and coverable lines are covered by tests :white_check_mark:",
            f"> Comparison is base [(`{comparison.base.commit.commitid[:7]}`)](test.example.br/gh/{repository.slug}/commit/{comparison.base.commit.commitid}?el=desc) 65.38% compared to head [(`{comparison.head.commit.commitid[:7]}`)](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=desc) 65.38%.",
            f"",
            f"[![Impacted file tree graph](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/graphs/tree.svg?width=650&height=150&src=pr&token={repository.image_token})](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=tree)",
            f"",
            f"```diff",
            f"@@           Coverage Diff           @@",
            f"##           master      #{pull.pullid}   +/-   ##",
            f"=======================================",
            f"  Coverage   65.38%   65.38%           ",
            f"=======================================",
            f"  Files          15       15           ",
            f"  Lines         208      208           ",
            f"=======================================",
            f"  Hits          136      136           ",
            f"  Misses          4        4           ",
            f"  Partials       68       68           ",
            f"```",
            f"",
            f"| [Flag](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flags) | Coverage Δ | |",
            f"|---|---|---|",
            f"| [unit](test.example.br/gh/{repository.slug}/pull/{pull.pullid}/flags?src=pr&el=flag) | `25.00% <ø> (ø)` | |",
            f"",
            f"Flags with carried forward coverage won't be shown. [Click here](https://docs.codecov.io/docs/carryforward-flags#carryforward-flags-in-the-pull-request-comment) to find out more."
            f"",
            f"",
            f"",
            f"------",
            f"",
            f"[Continue to review full report in "
            f"Codecov by Sentry](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=continue).",
            f"> **Legend** - [Click here to learn "
            f"more](https://docs.codecov.io/docs/codecov-delta)",
            f"> `Δ = absolute <relative> (impact)`, `ø = not affected`, `? = missing data`",
            f"> Powered by "
            f"[Codecov](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=footer). "
            f"Last update "
            f"[{comparison.base.commit.commitid[:7]}...{comparison.head.commit.commitid[:7]}](test.example.br/gh/{repository.slug}/pull/{pull.pullid}?src=pr&el=lastupdated). "
            f"Read the [comment docs](https://docs.codecov.io/docs/pull-request-comments).",
            f"",
        ]

        for exp, res in zip(expected_result, result):
            assert exp == res
        assert result == expected_result


class TestComponentWriterSection(object):
    @pytest.mark.asyncio
    async def test_write_message_component_section_empty(
        self,
        dbsession,
        mock_configuration,
        mock_repo_provider,
        sample_comparison,
    ):
        comparison = sample_comparison
        section_writer = ComponentsSectionWriter(
            repository=comparison.head.commit.repository,
            layout="layout",
            show_complexity=False,
            settings={},
            current_yaml={},
        )
        message = await section_writer.write_section(
            comparison=comparison, diff=None, changes=None, links={"pull": "urlurl"}
        )
        expected = []
        assert message == expected

    @pytest.mark.asyncio
    async def test_get_component_data_for_table(
        self,
        dbsession,
        mock_configuration,
        mock_repo_provider,
        sample_comparison,
    ):
        comparison = sample_comparison
        section_writer = ComponentsSectionWriter(
            repository=comparison.head.commit.repository,
            layout="layout",
            show_complexity=False,
            settings={},
            current_yaml={
                "component_management": {
                    "individual_components": [
                        {"component_id": "go_files", "paths": [r".*\.go"]},
                        {"component_id": "py_files", "paths": [r".*\.py"]},
                    ]
                }
            },
        )
        all_components = get_components_from_yaml(section_writer.current_yaml)
        comparison = sample_comparison
        component_data = await section_writer._get_table_data_for_components(
            all_components, comparison
        )
        print(component_data)
        expected_result = [
            {
                "name": "go_files",
                "before": ReportTotals(
                    files=1,
                    lines=4,
                    hits=2,
                    misses=2,
                    partials=0,
                    coverage="50.00000",
                    branches=0,
                    methods=0,
                    messages=0,
                    sessions=1,
                    complexity=11,
                    complexity_total=20,
                    diff=0,
                ),
                "after": ReportTotals(
                    files=1,
                    lines=8,
                    hits=5,
                    misses=3,
                    partials=0,
                    coverage="62.50000",
                    branches=0,
                    methods=0,
                    messages=0,
                    sessions=1,
                    complexity=10,
                    complexity_total=2,
                    diff=0,
                ),
                "diff": ReportTotals(
                    files=1,
                    lines=3,
                    hits=2,
                    misses=1,
                    partials=0,
                    coverage="66.66667",
                    branches=0,
                    methods=0,
                    messages=0,
                    sessions=0,
                    complexity=0,
                    complexity_total=0,
                    diff=0,
                ),
            },
            {
                "name": "py_files",
                "before": ReportTotals(
                    files=1,
                    lines=2,
                    hits=1,
                    misses=1,
                    partials=0,
                    coverage="50.00000",
                    branches=0,
                    methods=0,
                    messages=0,
                    sessions=1,
                    complexity=0,
                    complexity_total=0,
                    diff=0,
                ),
                "after": ReportTotals(
                    files=1,
                    lines=2,
                    hits=1,
                    misses=0,
                    partials=1,
                    coverage="50.00000",
                    branches=1,
                    methods=0,
                    messages=0,
                    sessions=1,
                    complexity=0,
                    complexity_total=0,
                    diff=0,
                ),
                "diff": ReportTotals(
                    files=0,
                    lines=0,
                    hits=0,
                    misses=0,
                    partials=0,
                    coverage=None,
                    branches=0,
                    methods=0,
                    messages=0,
                    sessions=0,
                    complexity=None,
                    complexity_total=None,
                    diff=0,
                ),
            },
        ]
        assert component_data == expected_result

    @pytest.mark.asyncio
    async def test_get_component_data_for_table_no_base(
        self,
        dbsession,
        mock_configuration,
        mock_repo_provider,
        sample_comparison,
    ):
        comparison = sample_comparison
        comparison.base.report = None
        comparison.base.commit = None
        section_writer = ComponentsSectionWriter(
            repository=comparison.head.commit.repository,
            layout="layout",
            show_complexity=False,
            settings={},
            current_yaml={
                "component_management": {
                    "individual_components": [
                        {"component_id": "go_files", "paths": [r".*\.go"]},
                        {"component_id": "py_files", "paths": [r".*\.py"]},
                    ]
                }
            },
        )
        all_components = get_components_from_yaml(section_writer.current_yaml)
        comparison = sample_comparison
        component_data = await section_writer._get_table_data_for_components(
            all_components, comparison
        )
        print(component_data)
        expected_result = [
            {
                "name": "go_files",
                "before": None,
                "after": ReportTotals(
                    files=1,
                    lines=8,
                    hits=5,
                    misses=3,
                    partials=0,
                    coverage="62.50000",
                    branches=0,
                    methods=0,
                    messages=0,
                    sessions=1,
                    complexity=10,
                    complexity_total=2,
                    diff=0,
                ),
                "diff": None,
            },
            {
                "name": "py_files",
                "before": None,
                "after": ReportTotals(
                    files=1,
                    lines=2,
                    hits=1,
                    misses=0,
                    partials=1,
                    coverage="50.00000",
                    branches=1,
                    methods=0,
                    messages=0,
                    sessions=1,
                    complexity=0,
                    complexity_total=0,
                    diff=0,
                ),
                "diff": None,
            },
        ]
        assert component_data == expected_result

    @pytest.mark.asyncio
    async def test_write_message_component_section(
        self,
        dbsession,
        mock_configuration,
        mock_repo_provider,
        sample_comparison,
    ):
        comparison = sample_comparison
        section_writer = ComponentsSectionWriter(
            repository=comparison.head.commit.repository,
            layout="layout",
            show_complexity=False,
            settings={},
            current_yaml={
                "component_management": {
                    "individual_components": [
                        {"component_id": "go_files", "paths": [r".*\.go"]},
                        {"component_id": "py_files", "paths": [r".*\.py"]},
                    ]
                }
            },
        )
        message = await section_writer.write_section(
            comparison=comparison, diff=None, changes=None, links={"pull": "urlurl"}
        )
        expected = [
            "| [Components](urlurl/components?src=pr&el=components) | Coverage Δ | |",
            "|---|---|---|",
            "| [go_files](urlurl/components?src=pr&el=component) | `62.50% <66.67%> (+12.50%)` | :arrow_up: |",
            "| [py_files](urlurl/components?src=pr&el=component) | `50.00% <ø> (ø)` | |",
        ]
        assert message == expected

    @pytest.mark.asyncio
    async def test_write_message_component_section_no_base(
        self,
        dbsession,
        mock_configuration,
        mock_repo_provider,
        sample_comparison,
    ):
        comparison = sample_comparison
        comparison.base.report = None
        comparison.base.commit = None
        section_writer = ComponentsSectionWriter(
            repository=comparison.head.commit.repository,
            layout="layout",
            show_complexity=False,
            settings={},
            current_yaml={
                "component_management": {
                    "individual_components": [
                        {"component_id": "go_files", "paths": [r".*\.go"]},
                        {"component_id": "py_files", "paths": [r".*\.py"]},
                    ]
                }
            },
        )
        message = await section_writer.write_section(
            comparison=comparison, diff=None, changes=None, links={"pull": "urlurl"}
        )
        expected = [
            "| [Components](urlurl/components?src=pr&el=components) | Coverage Δ | |",
            "|---|---|---|",
            "| [go_files](urlurl/components?src=pr&el=component) | `62.50% <0.00%> (?)` | |",
            "| [py_files](urlurl/components?src=pr&el=component) | `50.00% <0.00%> (?)` | |",
        ]
        assert message == expected


class TestCommentNotifierWelcome:
    @pytest.mark.asyncio
    async def test_build_message(
        self, dbsession, mock_configuration, mock_repo_provider, sample_comparison
    ):
        mock_configuration.params["setup"]["codecov_dashboard_url"] = "test.example.br"
        notifier = CommentNotifier(
            repository=sample_comparison.head.commit.repository,
            title="title",
            notifier_yaml_settings={"layout": "reach, diff, flags, files, footer"},
            notifier_site_settings=True,
            current_yaml={},
        )
        result = await notifier.build_message(sample_comparison)
        expected_result = [
            "## Welcome to [Codecov](https://codecov.io) :tada:",
            "",
            "Once merged to your default branch, Codecov will compare your coverage reports and display the results in this comment.",
            "",
            "Thanks for integrating Codecov - We've got you covered :open_umbrella:",
        ]
        for exp, res in zip(expected_result, result):
            assert exp == res
        assert result == expected_result
