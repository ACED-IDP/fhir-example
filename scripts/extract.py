import asyncio
import logging
import time
from pathlib import Path
from typing import Iterator, TextIO

import aiohttp
import click
import orjson
import requests
from fhir.resources.bundle import BundleEntryRequest

logging.basicConfig(format='%(asctime)s %(message)s', encoding='utf-8', level=logging.INFO)
logger = logging.getLogger(__name__)

# no special headers for read
headers = {}


def read_resources(extract_path, url_base, url_path):
    """Read a resource from FHIR server, save it to file."""
    url = f"{url_base}/{url_path}"
    count = 0
    tic = time.perf_counter()

    # open file pointers
    emitters = {}

    def emitter(name: str) -> TextIO:
        """Maintain a hash of open files."""
        if name not in emitters:
            emitters[name] = open(extract_path / f"{name}.ndjson", "w")
        return emitters[name]

    response = requests.get(url)
    response.raise_for_status()
    response_json = response.json()
    if "resourceType" in response_json:
        if response_json["resourceType"] == "Bundle":
            if "entry" in response_json:
                for entry in response_json['entry']:
                    resource = entry['resource']
                    fp = emitter(resource['resourceType'])
                    fp.write(orjson.dumps(resource, option=orjson.OPT_APPEND_NEWLINE).decode())
                    count += 1
            toc = time.perf_counter()
            if count:
                logger.info(f"GET {url} seconds:{toc - tic:0.4f} count:{count} avg:{(toc - tic) / count:0.4f}/sec")
            else:
                logger.info(f"GET {url} seconds:{toc - tic:0.4f} returned no resources")
        else:
            fp = emitter(response_json['resourceType'])
            fp.write(orjson.dumps(response_json, option=orjson.OPT_APPEND_NEWLINE).decode())
            toc = time.perf_counter()
            count += 1
            logger.info(f"GET {url} seconds:{toc - tic:0.4f} count:{count} avg:{(toc - tic) / count:0.4f}/sec")

    # close all emitters
    for fp_ in emitters.values():
        fp_.close()


@click.group()
def extract():
    """Query FHIR resources, write to .ndjson file."""
    pass


@extract.command('resources')
@click.option('--extract_path', default='data/output/resources', show_default=True,
              help='Where to store extracted data (ndjson)')
@click.option('--url_base', default="http://localhost:8090/fhir", show_default=True,
              help='url to HAPI FHIR server [base]')
@click.option('--url_path', default='metadata', show_default=True,
              help='FHIR url path [type]/[id] {?_format=[mime-type]}')
def resources(extract_path, url_base, url_path):
    """Query FHIR resources, write to .ndjson file."""
    read_resources(Path(extract_path), url_base, url_path)


if __name__ == '__main__':
    extract()

"""
Ad hoc testing These queries should work
 curl http://localhost:8090/fhir/Questionnaire 
"""