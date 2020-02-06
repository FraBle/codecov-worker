import pytest

from services.notification.notifiers.comment import CommentNotifier
from database.tests.factories import CommitFactory, PullFactory, RepositoryFactory
from services.notification.types import FullCommit, Comparison



@pytest.fixture
def sample_comparison(dbsession, request, sample_report, small_report):
    repository = RepositoryFactory.create(
        owner__username='ThiagoCodecov',
        name='example-python',
        owner__unencrypted_oauth_token='testtlxuu2kfef3km1fbecdlmnb2nvpikvmoadi3',
        image_token='abcdefghij'
    )
    dbsession.add(repository)
    dbsession.flush()
    base_commit = CommitFactory.create(
        repository=repository, commitid='4535be18e90467d6d9a99c0ce651becec7f7eba6'
    )
    head_commit = CommitFactory.create(
        repository=repository, branch='new_branch', commitid='2e2600aa09525e2e1e1d98b09de61454d29c94bb'
    )
    pull = PullFactory.create(
        repository=repository,
        base=base_commit.commitid,
        head=head_commit.commitid,
        pullid=15
    )
    dbsession.add(base_commit)
    dbsession.add(head_commit)
    dbsession.add(pull)
    dbsession.flush()
    repository = base_commit.repository
    base_full_commit = FullCommit(commit=base_commit, report=small_report)
    head_full_commit = FullCommit(commit=head_commit, report=sample_report)
    return Comparison(
        head=head_full_commit,
        base=base_full_commit,
        pull=pull
    )


class TestCommentNotifierIntegration(object):

    @pytest.mark.asyncio
    async def test_notify(self, sample_comparison, codecov_vcr):
        comparison = sample_comparison
        notifier = CommentNotifier(
            repository=comparison.head.commit.repository,
            title='title',
            notifier_yaml_settings={'layout': "reach, diff, flags, files, footer"},
            notifier_site_settings=True,
            current_yaml={}
        )
        result = await notifier.notify(comparison)
        assert result.notification_attempted
        assert result.notification_successful
        assert result.explanation is None
        message = [
            '# [Codecov](None/gh/ThiagoCodecov/example-python/pull/15?src=pr&el=h1) Report',
            '> Merging [#15](None/gh/ThiagoCodecov/example-python/pull/15?src=pr&el=desc) into [master](None/gh/ThiagoCodecov/example-python/commit/4535be18e90467d6d9a99c0ce651becec7f7eba6&el=desc) will **increase** coverage by `10.00%`.',
            '> The diff coverage is `n/a`.',
            '',
            '[![Impacted file tree graph](None/gh/ThiagoCodecov/example-python/pull/15/graphs/tree.svg?width=650&height=150&src=pr&token=abcdefghij)](None/gh/ThiagoCodecov/example-python/pull/15?src=pr&el=tree)',
            '',
            '```diff',
            '@@              Coverage Diff              @@',
            '##             master      #15       +/-   ##',
            '=============================================',
            '+ Coverage     50.00%   60.00%   +10.00%     ',
            '+ Complexity       11       10        -1     ',
            '=============================================',
            '  Files             2        2               ',
            '  Lines             6       10        +4     ',
            '  Branches          0        1        +1     ',
            '=============================================',
            '+ Hits              3        6        +3     ',
            '  Misses            3        3               ',
            '- Partials          0        1        +1     ',
            '```',
            '',
            '| Flag | Coverage Δ | Complexity Δ | |',
            '|---|---|---|---|',
            '| #integration | `?` | `?` | |',
            '| #unit | `100.00% <ø> (?)` | `0.00 <ø> (?)` | |',
            '',
            '| [Impacted Files](None/gh/ThiagoCodecov/example-python/pull/15?src=pr&el=tree) | Coverage Δ | Complexity Δ | |',
            '|---|---|---|---|',
            '| [file\\_2.py](None/gh/ThiagoCodecov/example-python/pull/15/diff?src=pr&el=tree#diff-ZmlsZV8yLnB5) | `50.00% <0.00%> (ø)` | `0.00% <0.00%> (ø%)` | :arrow_up: |',
            '| [file\\_1.go](None/gh/ThiagoCodecov/example-python/pull/15/diff?src=pr&el=tree#diff-ZmlsZV8xLmdv) | `62.50% <0.00%> (+12.50%)` | `10.00% <0.00%> (-1.00%)` | :arrow_up: |',
            '',
            '------',
            '',
            '[Continue to review full report at Codecov](None/gh/ThiagoCodecov/example-python/pull/15?src=pr&el=continue).',
            '> **Legend** - [Click here to learn more](https://docs.codecov.io/docs/codecov-delta)',
            '> `Δ = absolute <relative> (impact)`, `ø = not affected`, `? = missing data`',
            '> Powered by [Codecov](None/gh/ThiagoCodecov/example-python/pull/15?src=pr&el=footer). Last update [30cc1ed...2e2600a](None/gh/ThiagoCodecov/example-python/pull/15?src=pr&el=lastupdated). Read the [comment docs](https://docs.codecov.io/docs/pull-request-comments).',
            ''
        ]
        for exp, res in zip(result.data_sent['message'], message):
            assert exp == res
        assert result.data_sent['message'] == message
        assert result.data_sent == {
            'commentid': None,
            'message': message,
            'pullid': 15
        }
        assert result.data_received == {'id': 570682170}