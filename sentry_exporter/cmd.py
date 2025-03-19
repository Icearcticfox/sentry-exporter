import threading

import click
import logging
import asyncio
from datetime import datetime
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from prometheus_client import make_wsgi_app
from sentry_exporter.core.sentry import SentryAPI
from sentry_exporter.utils.health import app
from logging import config
from werkzeug.serving import run_simple

log_config = {
    "version": 1,
    "root": {"handlers": ["console"], "level": "INFO"},
    "handlers": {
        "console": {
            "formatter": "std_out",
            "class": "logging.StreamHandler",
            "level": "INFO",
        }
    },
    "formatters": {
        "std_out": {
            "format": "%(asctime)s : %(levelname)s : %(module)s : %(funcName)s : L%(lineno)d : %(message)s",
            "datefmt": "%d-%m-%Y %I:%M:%S",
        }
    },
}

config.dictConfig(log_config)


@click.option("--sentry-token", "-T", required=True)
@click.option("--sentry-url", "sentry_url", required=True)
@click.option("--sentry-org", "sentry_org", required=True)
@click.option("--metrics-port", "metrics_port", default=8000, type=int)
@click.option("--max-con-req", "max_concurrent_requests", default=5, type=int)
@click.command("Runs sentry exporter")
def run_exporter(
    sentry_token, sentry_url, sentry_org, metrics_port, max_concurrent_requests
):
    async def run():
        sentry_api = SentryAPI(
            sentry_token=sentry_token,
            sentry_org=sentry_org,
            sentry_url=sentry_url,
            max_concurrent_requests=max_concurrent_requests,
        )

        logging.info(max_concurrent_requests)
        retry_limit = 5
        while True:
            try:
                logging.info(
                    "Start scraping from Sentry Api. "
                    + str(datetime.now().strftime("%d-%m-%Y %I:%M:%S"))
                )
                await sentry_api.enrich_projects_with_rate_limits_and_stats()
                logging.info(
                    "Waiting next scrape. "
                    + str(datetime.now().strftime("%d-%m-%Y %I:%M:%S"))
                )
                await asyncio.sleep(30)
                retry_limit = 5
            except Exception as e:
                if retry_limit == 0:
                    logging.error("Retry limit reached", exc_info=e)
                    exit(1)
                logging.error("Something went wrong: %s, try again", exc_info=e)
                retry_limit -= 1

    # Start Prometheus metrics server and Flask app using DispatcherMiddleware
    def start_flask():
        app_dispatch = DispatcherMiddleware(
            app, {"/metrics": make_wsgi_app(), "/": make_wsgi_app()}
        )
        run_simple("0.0.0.0", metrics_port, app_dispatch)

    flask_thread = threading.Thread(target=start_flask)
    flask_thread.daemon = True
    flask_thread.start()

    asyncio.run(run())


def main():
    run_exporter()


if __name__ == "__main__":
    main()
