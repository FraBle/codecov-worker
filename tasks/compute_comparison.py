from collections import namedtuple
import logging

from shared.celery_config import compute_comparison_task_name
from shared.reports.readonly import ReadOnlyReport
from shared.reports.types import Change

from app import celery_app
from tasks.base import BaseCodecovTask
from database.models import CompareCommit
from database.enums import CompareCommitState
from services.archive import ArchiveService
from services.comparison import ComparisonProxy
from services.comparison.types import Comparison, FullCommit
from services.report import ReportService
from services.repository import get_repo_provider_service
from services.yaml import get_current_yaml
from services.notification.notifiers.mixins.message import make_metrics

log = logging.getLogger(__name__)
null = namedtuple("_", ["totals"])(None)


class ComputeComparisonTask(BaseCodecovTask):
    name = compute_comparison_task_name

    async def run_async(self, db_session, comparison_id, *args, **kwargs):
        log.info(f"Computing comparison", extra=dict(comparison_id=comparison_id))
        comparison = db_session.query(CompareCommit).get(comparison_id)
        current_yaml = await self.get_yaml_commit(comparison.compare_commit)
        comparison_proxy = await self.get_comparison_proxy(comparison, current_yaml)
        unexpected_changes = await comparison_proxy.get_changes()
        changes_in_diff = await self.get_diff_as_changes(comparison_proxy, current_yaml)
        impacted_files = unexpected_changes + changes_in_diff
        dict_impacted_files = self.serialize_impacted_files(impacted_files, comparison_proxy)
        path = self.store_results(comparison, dict_impacted_files)
        comparison.report_storage_path = path
        comparison.state = CompareCommitState.processed
        log.info(f"Computing comparison successful", extra=dict(comparison_id=comparison_id))
        return {"successful": True}

    async def get_yaml_commit(self, commit):
        repository_service = get_repo_provider_service(commit.repository)
        return await get_current_yaml(commit, repository_service)

    async def get_comparison_proxy(self, comparison, current_yaml):
        compare_commit = comparison.compare_commit
        base_commit = comparison.base_commit
        report_service = ReportService(current_yaml)
        base_report = report_service.get_existing_report_for_commit(
            base_commit, report_class=ReadOnlyReport
        )
        compare_report = report_service.get_existing_report_for_commit(
            compare_commit, report_class=ReadOnlyReport
        )
        return ComparisonProxy(
            Comparison(
                head=FullCommit(commit=compare_commit, report=compare_report),
                enriched_pull=None,
                base=FullCommit(commit=base_commit, report=base_report),
            )
        )

    async def get_diff_as_changes(self, comparison_proxy, current_yaml):
        diff = await comparison_proxy.get_diff()
        comparison_proxy.head.report.apply_diff(diff)
        return [
            Change(
                path=path,
                new=file_data.get('type') == 'added',
                deleted=file_data.get('type') == 'deleted',
                in_diff=True,
                old_path=file_data.get("before"),
                totals=file_data.get("totals")
            )
            for path, file_data in diff.get("files", []).items()
            if file_data.get("totals")
        ]

    def serialize_impacted_files(self, impacted_files, comparison_proxy):
        base_report = comparison_proxy.base.report
        head_report = comparison_proxy.head.report
        files_in_dict = []
        for file in impacted_files:
            path = file.path
            before = base_report.get(path, null).totals
            after = head_report.get(path, null).totals
            files_in_dict.append({
                "path": file.path,
                "base_totals": before.astuple() if before else None,
                "compare_totals": after.astuple() if after else None,
                "patch": file.totals.astuple(),
                "new": file.new,
                "deleted": file.deleted,
                "in_diff": file.in_diff,
                "old_path": file.old_path,
            })
        return files_in_dict

    def store_results(self, comparison, impacted_files):
        repository = comparison.compare_commit.repository
        storage_service = ArchiveService(repository)
        return storage_service.write_computed_comparison(comparison, impacted_files)


RegisteredComputeComparisonTask = celery_app.register_task(ComputeComparisonTask())
compute_comparison_task = celery_app.tasks[RegisteredComputeComparisonTask.name]
