# BioCommons Access Login Proxy for AAF

This is a standalone login proxy for BioCommons Access, to improve user experience
when users are connecting via AAF.

The proxy accepts `/authorize` requests from Auth0, determines the user's
institution based on their email domain, and adds the institution's `entityID`
to the request before redirecting to AAF login. This allows the user to
skip the AAF Discovery Service.

## Architecture

The proxy consists of two parts:

* A simple FastAPI application, that largely just handles the `/authorize`
  endpoint.
* A valkey cache, to store the AAF metadata for each institution.

## Config/Environment Variables

See `config.py` and `.env.example` for the environment variables that are used.
The most important variables are:

* `AAF_METADATA_URL`: URL for the metadata XML AAF provides (different for test/prod)
* `AAF_PUBKEY_URL`: public key for the certificate used to sign the metadata XML
* `AAF_AUTHORIZE_URL`: URL to redirect to for AAF login

The project uses `pydantic-settings` to manage config, and can read from
either `.env` or environment variables (environment variables override `.env`)..
Copy `.env.example` to `.env` and modify for local development.

## Development

Install dependencies:

```shell
uv sync --dev
```

Set up pre-commit checks:

```shell
uv run pre-commit install
```

Run tests:

```shell
uv run pytest
```

Run the app via Docker Compose (easiest way to run the app + Valkey). The API:
will be available at `http://localhost:8000/`

```shell
docker compose up
```
