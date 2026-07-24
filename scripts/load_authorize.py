#!/usr/bin/env python3
"""
Simple load-testing script to ping the /authorize endpoint
with simultaneous requests. The /authorize endpoint
returns a redirect to AAF, as long as we don't follow
the redirect it won't send anything on to AAF.
"""

import argparse
import asyncio
import random
import time
from dataclasses import dataclass
from urllib.parse import urljoin

import httpx
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
)


DEFAULT_DOMAINS = (
    "sydney.edu.au",
    "unimelb.edu.au",
    "unsw.edu.au",
    "uq.edu.au",
    "monash.edu",
)


@dataclass(frozen=True)
class RequestResult:
    email: str
    status_code: int | None
    location: str | None
    elapsed_seconds: float
    error: str | None = None

    @property
    def redirected(self) -> bool:
        return (
            self.error is None
            and self.status_code is not None
            and 300 <= self.status_code < 400
            and self.location is not None
        )


@dataclass(frozen=True)
class LoadTestResult:
    requests: list[RequestResult]
    elapsed_seconds: float


def authorize_url(base_url: str) -> str:
    if base_url.endswith("/authorize"):
        return base_url
    return urljoin(base_url.rstrip("/") + "/", "authorize")


def make_email(index: int, domains: tuple[str, ...]) -> str:
    domain = random.choice(domains)
    return f"load-test-{index}@{domain}"


async def send_authorize_request(
    client: httpx.AsyncClient,
    url: str,
    email: str,
    semaphore: asyncio.Semaphore,
) -> RequestResult:
    async with semaphore:
        started_at = time.perf_counter()
        try:
            response = await client.get(
                url,
                params={"screen_name": email},
                follow_redirects=False,
            )
        except httpx.HTTPError as exc:
            return RequestResult(
                email=email,
                status_code=None,
                location=None,
                elapsed_seconds=time.perf_counter() - started_at,
                error=str(exc),
            )

        return RequestResult(
            email=email,
            status_code=response.status_code,
            location=response.headers.get("location"),
            elapsed_seconds=time.perf_counter() - started_at,
        )


async def run_load_test(
    base_url: str,
    requests: int,
    concurrency: int,
    domains: tuple[str, ...],
    timeout: float,
) -> LoadTestResult:
    url = authorize_url(base_url)
    semaphore = asyncio.Semaphore(concurrency)
    results: list[RequestResult] = []
    started_at = time.perf_counter()
    async with httpx.AsyncClient(timeout=timeout) as client:
        tasks = [
            send_authorize_request(
                client=client,
                url=url,
                email=make_email(index, domains),
                semaphore=semaphore,
            )
            for index in range(requests)
        ]
        with Progress(
            TextColumn("{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
        ) as progress:
            progress_task = progress.add_task("Requests", total=requests)
            for task in asyncio.as_completed(tasks):
                results.append(await task)
                progress.advance(progress_task)
    return LoadTestResult(
        requests=results,
        elapsed_seconds=time.perf_counter() - started_at,
    )


def print_summary(load_test_result: LoadTestResult) -> None:
    results = load_test_result.requests
    total = len(results)
    redirected = sum(result.redirected for result in results)
    failed = total - redirected
    elapsed = [result.elapsed_seconds for result in results]
    print(f"Requests: {total}")
    print(f"Redirects: {redirected}")
    print(f"Failures: {failed}")
    print(f"Total time: {load_test_result.elapsed_seconds:.3f}s")
    print(f"Min latency: {min(elapsed):.3f}s")
    print(f"Max latency: {max(elapsed):.3f}s")
    print(f"Avg latency: {sum(elapsed) / total:.3f}s")

    if failed:
        print()
        print("Failures:")
        for result in results:
            if not result.redirected:
                detail = result.error or f"status={result.status_code}"
                print(f"- {result.email}: {detail}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send simultaneous requests to the deployed /authorize endpoint."
    )
    parser.add_argument(
        "base_url",
        help="Deployment base URL, or the full /authorize URL.",
    )
    parser.add_argument(
        "-n",
        "--requests",
        type=int,
        default=20,
        help="Total number of requests to send.",
    )
    parser.add_argument(
        "-c",
        "--concurrency",
        type=int,
        default=5,
        help="Maximum number of simultaneous requests.",
    )
    parser.add_argument(
        "--domain",
        dest="domains",
        action="append",
        help="University email domain to use. Can be passed more than once.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Per-request timeout in seconds.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    domains = tuple(args.domains or DEFAULT_DOMAINS)
    if args.requests < 1:
        raise SystemExit("--requests must be at least 1")
    if args.concurrency < 1:
        raise SystemExit("--concurrency must be at least 1")

    load_test_result = asyncio.run(
        run_load_test(
            base_url=args.base_url,
            requests=args.requests,
            concurrency=args.concurrency,
            domains=domains,
            timeout=args.timeout,
        )
    )
    print_summary(load_test_result)

    if any(not result.redirected for result in load_test_result.requests):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
