#!/usr/bin/env python3

import sys
import time
import requests
import singer
import backoff
import copy

from datetime import datetime, timedelta

base_url = 'https://api.currencylayer.com/historical'

logger = singer.get_logger()
session = requests.Session()

DATE_FORMAT = '%Y-%m-%d'

REQUIRED_CONFIG_KEYS = [
    'base',
    'access_key',
    'start_date'
]


def parse_response(r):
    flattened = r['quotes']
    flattened[r['source'] + r['source']] = 1.0
    flattened['date'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.strptime(r['date'], DATE_FORMAT))
    return flattened


schema = {'type': 'object',
          'properties':
              {'date': {'type': 'string',
                        'format': 'date-time'}}}


def giveup(error):
    logger.error(error.response.text)
    response = error.response
    return not (response.status_code == 429 or
                response.status_code >= 500)


@backoff.on_exception(backoff.constant,
                      (requests.exceptions.RequestException),
                      jitter=backoff.random_jitter,
                      max_tries=5,
                      giveup=giveup,
                      interval=30)
def request(url, params):
    response = requests.get(url=url, params=params)
    response.raise_for_status()
    return response


def do_sync(base, start_date, access_key):
    state = {'start_date': start_date}
    next_date = start_date
    prev_schema = {}

    try:
        while datetime.strptime(next_date, DATE_FORMAT) <= datetime.utcnow():
            logger.info('Replicating exchange rate data from %s using base %s',
                        next_date,
                        base)

            response = request(base_url, {'source': base, 'access_key': access_key, 'date': next_date})
            payload = response.json()

            logger.info(payload)
            flattened = parse_response(payload)
            # Update schema if new currency/currencies exist
            for rate in payload['quotes']:
                if rate != 'date' and rate not in schema['properties']:
                    schema['properties'][rate] = {'type': ['null', 'number']}

            # Only write schema if it has changed
            if schema != prev_schema:
                singer.write_schema('exchange_rate', schema, 'date')

            if payload['date'] == next_date:
                singer.write_records('exchange_rate', [flattened])

            state = {'start_date': next_date}
            next_date = (datetime.strptime(next_date, DATE_FORMAT) + timedelta(days=1)).strftime(DATE_FORMAT)
            prev_schema = copy.deepcopy(schema)

    except requests.exceptions.RequestException as e:
        logger.fatal('Error on ' + e.request.url +
                     '; received status ' + str(e.response.status_code) +
                     ': ' + e.response.text)
        singer.write_state(state)
        sys.exit(-1)

    singer.write_state(state)
    logger.info('Tap exiting normally')


def main():
    args = singer.utils.parse_args(REQUIRED_CONFIG_KEYS)
    config = args.config or {}
    state = args.state or {}

    start_date = state.get('start_date') or config.get('start_date') or datetime.utcnow().strftime(DATE_FORMAT)
    start_date = singer.utils.strptime_with_tz(start_date).date().strftime(DATE_FORMAT)
    access_key = config.get('access_key')

    do_sync(config.get('base', 'USD'), start_date, access_key)


if __name__ == '__main__':
    main()
