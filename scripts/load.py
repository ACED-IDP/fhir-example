import asyncio
import logging
import time
from pathlib import Path
from typing import Iterator

import aiohttp
import click
import orjson
from fhir.resources.bundle import BundleEntryRequest

logging.basicConfig(format='%(asctime)s %(message)s', encoding='utf-8', level=logging.INFO)
logger = logging.getLogger(__name__)


def bundle_entry_request_as_json(self, strict=True):  # noqa F841
    """Preserve the IDs. Patched as_json to PUT not post see https://github.com/hapifhir/hapi-fhir/issues/333."""
    if self.method == 'POST' and self._owner.resource.id:
        self.method = 'PUT'
        self.url += f"/{self._owner.resource.id}"
    return {'method': self.method, 'url': self.url}


BundleEntryRequest.as_json = bundle_entry_request_as_json

# performance improvement
# see https://hapifhir.io/hapi-fhir/docs/server_jpa/performance.html#disable-upsert-existence-check
headers = {
    "Content-Type": "application/fhir+json;charset=utf-8",
    "X-Upsert-Extistence-Check": "disabled",
}


def _chunker(seq: Iterator, size: int) -> Iterator:
    """Iterate over a list in chunks.

    Args:
        seq: an iterable
        size: desired chunk size

    Returns:
        an iterator that returns lists of size or less
    """
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))


async def load_bundle(path, url):
    """Read a bundle, load it to server."""
    print(path)
    session = None
    try:
        tic = time.perf_counter()
        with open(path, 'r') as data:
            bundle = data.read()
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(url=url, data=bundle) as response:
                if response.status != 200:
                    logger.error(await response.json())
                response.raise_for_status()
        session = None
        toc = time.perf_counter()
        logger.info(f"POST {path} {toc - tic:0.4f} seconds")
        return True
    finally:
        if session:
            await session.close()


async def load_resource(path, url):
    """Read a resource from path, load it to server."""
    print(path)
    session = None
    count = 0
    try:
        tic = time.perf_counter()
        with open(path, 'r') as data:
            for line in data.readlines():
                obj = orjson.loads(line)
                item_url = f"{url}/{obj['resourceType']}/{obj['id']}"
                async with aiohttp.ClientSession(headers=headers) as session:
                    async with session.put(url=item_url, json=obj) as response:
                        if response.status > 201:
                            rsp = await response.json()
                            print(response.status, rsp, obj)
                        response.raise_for_status()
                        count += 1
        session = None
        toc = time.perf_counter()
        logger.info(f"POST {path} seconds:{toc - tic:0.4f} count:{count} avg:{(toc - tic) / count:0.4f}/sec")
        return True
    finally:
        if session:
            await session.close()


async def load_resources(paths, url, chunk_size):
    """Load paths of resources."""
    limit = None
    count = 0
    ok = True

    paths = [_ for _ in paths]

    for chunk in _chunker(paths, chunk_size):
        tasks = []

        for path in chunk:
            task = asyncio.create_task(load_resource(path=path, url=url))
            tasks.append(task)
            count += 1
            if limit and count == limit:
                break

        ok = all([
            await ok_
            for ok_ in asyncio.as_completed(tasks)
        ])

        if limit and count == limit:
            break
    return ok


async def load_bundles(paths, url, chunk_size):
    """Load paths of bundles."""
    limit = None
    count = 0
    ok = True

    paths = [_ for _ in paths]

    for chunk in _chunker(paths, chunk_size):
        tasks = []

        for path in chunk:
            task = asyncio.create_task(load_bundle(path=path, url=url))
            tasks.append(task)
            count += 1
            if limit and count == limit:
                break

        ok = all([
            await ok_
            for ok_ in asyncio.as_completed(tasks)
        ])

        if limit and count == limit:
            break
    return ok


@click.group()
def load():
    """Load files to FHIR server."""
    pass


@load.command('bundles')
@click.option('--input_path', default='data/input/bundles', show_default=True,
              help='Where to find data to import (json, ndjson)')
@click.option('--url', default="http://localhost:8090/fhir", show_default=True,
              help='url to HAPI FHIR server')
@click.option('--chunk_size', default=5, show_default=True,
              help='Number of simultaneous loaders')
def bundles(input_path, url, chunk_size):
    """Load bundles (.json)."""
    asyncio.run(load_bundles(Path(input_path).glob('*.json'), url, chunk_size))
    logger.info('done')


@load.command('resources')
@click.option('--input_path', default='data/input/resources', show_default=True,
              help='Where to find data to import (json, ndjson)')
@click.option('--url', default="http://localhost:8090/fhir", show_default=True,
              help='url to HAPI FHIR server')
@click.option('--chunk_size', default=5, show_default=True,
              help='Number of simultaneous loaders')
def resources(input_path, url, chunk_size):
    """Load resources (.ndjson)."""
    asyncio.run(load_resources(Path(input_path).glob('*.ndjson'), url, chunk_size))
    logger.info('done')


if __name__ == '__main__':
    load()

"""
Ad hoc testing These queries should work
 curl http://localhost:8090/fhir/Questionnaire 
"""