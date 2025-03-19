# Sentry Exporter

Simple exporter metrics from sentry

## Contribute: build & test

```sh
virtualenv -p python3.9 .venv
source .venv/bin/activate

pip install -r requirements.txt
pip install -e .
```

## Lint & test

```sh
black .
```

## Configuration

Mandatory parameter:  
`--sentry-org`, `--sentry-url` and `--sentry-token`/ `-T`

## Run the exporter

```sh
sentry-exporter --sentry-org $SENTRY_ORG --sentry-url $SENTRY_URL -T $SENTRY_KEY
```
