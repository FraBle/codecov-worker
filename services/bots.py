import logging

from services.github import get_github_integration_token
from services.encryption import encryptor

log = logging.getLogger(__name__)


class RepositoryWithoutValidBotError(Exception):
    pass


def get_repo_appropriate_bot_token(repo):
    if repo.using_integration and repo.owner.integration_id:
        github_token = get_github_integration_token(repo.owner.service, repo.owner.integration_id)
        return dict(key=github_token)
    return encryptor.decrypt_token(_get_repo_appropriate_bot(repo).oauth_token)


def _get_repo_appropriate_bot(repo):
    if repo.bot is not None and repo.bot.oauth_token is not None:
        log.info("Repo has specific bot", extra=dict(repoid=repo.repoid, botid=repo.bot.ownerid))
        return repo.bot
    if repo.owner.bot is not None and repo.owner.bot.oauth_token is not None:
        log.info(
            "Repo Owner has specific bot",
            extra=dict(repoid=repo.repoid, botid=repo.owner.bot.ownerid, ownerid=repo.owner.ownerid)
        )
        return repo.owner.bot
    if repo.owner.oauth_token is not None:
        log.info(
            "Using repo owner as bot fallback",
            extra=dict(repoid=repo.repoid, ownerid=repo.owner.ownerid)
        )
        return repo.owner
    raise RepositoryWithoutValidBotError()