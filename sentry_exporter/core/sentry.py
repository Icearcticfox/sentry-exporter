import logging

import aiohttp
import asyncio
from datetime import datetime, timedelta
from prometheus_client import Gauge


class SentryAPI:

    def __init__(
        self,
        sentry_token: str,
        sentry_org: str,
        sentry_url: str,
        max_concurrent_requests: int,
    ):
        self._sentry_token = sentry_token
        self._sentry_org = sentry_org
        self._sentry_url = sentry_url
        self._semaphore = asyncio.Semaphore(max_concurrent_requests)
        self._sentry_hourly_rate_limit = Gauge(
            "sentry_hourly_rate_limit", "Rate limit for Sentry projects", ["project"]
        )
        self._sentry_received_event_hourly_rate = Gauge(
            "sentry_received_event_hourly_rate",
            "Received events for Sentry projects",
            ["project"],
        )

    async def _get(self, url: str) -> dict:
        async with self._semaphore:
            headers = {"Authorization": f"Bearer {self._sentry_token}"}
            async with aiohttp.ClientSession(headers=headers) as session:
                while True:
                    async with session.get(url) as response:
                        if response.status == 429:  # Too Many Requests
                            retry_after = int(response.headers.get("Retry-After", 1))
                            logging.warning(
                                "Rate limit exceeded, retrying after %s seconds...",
                                retry_after,
                            )
                            await asyncio.sleep(retry_after)
                            continue
                        response.raise_for_status()
                        return await response.json()

    async def _get_projects(self) -> dict:
        url = f"{self._sentry_url}organizations/{self._sentry_org}/projects/?all_projects=1"
        return await self._get(url)

    async def _get_rate_limit(self, project_slug: str) -> int:
        """Return client key rate limits configuration on an individual project."""
        rate_limit_url = (
            f"{self._sentry_url}projects/{self._sentry_org}/{project_slug}/keys/"
        )
        resp = await self._get(rate_limit_url)
        if resp and resp[0].get("rateLimit"):
            rate_limit_window = resp[0].get("rateLimit").get("window")
            rate_limit_count = resp[0].get("rateLimit").get("count")
            rate_limit_second = rate_limit_count / rate_limit_window
        else:
            rate_limit_second = 0

        rate_limit_hours = int(round((rate_limit_second * 60 * 60), 10))
        self._sentry_hourly_rate_limit.labels(project=project_slug).set(
            rate_limit_hours
        )
        return rate_limit_hours

    async def _get_project_stats(self, project_slug: str, project_id: str) -> dict:
        now = datetime.timestamp(datetime.utcnow())
        one_hour_ago = datetime.timestamp(datetime.utcnow() - timedelta(hours=1))
        stat_names = ["received", "rejected", "blacklisted"]
        project_stats = {}

        tasks = []
        for stat_name in stat_names:
            url = (
                f"{self._sentry_url}projects/{self._sentry_org}/{project_slug}/stats/"
                f"?stat={stat_name}&since={one_hour_ago}&until={now}&project={project_id}"
            )
            tasks.append(self._get(url))

        stats_responses = await asyncio.gather(*tasks)

        for stat_name, stats in zip(stat_names, stats_responses):
            events = sum(stat[1] for stat in stats if type(stat) is not str)
            project_stats[stat_name] = events

        self._sentry_received_event_hourly_rate.labels(project=project_slug).set(
            project_stats.get("received", 0)
        )
        return project_stats

    async def _update_project_metrics(self, project_info: dict) -> dict:
        project_slug = project_info["slug"]

        project_rate_limits = await self._get_rate_limit(project_slug)
        project_info["rate-limits"] = project_rate_limits

        project_stats = await self._get_project_stats(project_slug, project_info["id"])
        project_info["stats"] = project_stats

        return project_info

    async def enrich_projects_with_rate_limits_and_stats(self) -> list:
        projects = await self._get_projects()

        tasks = []
        for project in projects:
            project_info = {
                "id": project["id"],
                "slug": project["slug"],
                "name": project["name"],
            }
            tasks.append(self._update_project_metrics(project_info))

        enriched_projects = await asyncio.gather(*tasks)
        return enriched_projects
