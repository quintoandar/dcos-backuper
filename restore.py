#!/usr/bin/python

import argparse
import logging
import json
import requests
import sys

LOGGING_FORMAT = ('%(asctime)s - %(name)s - %(threadName)s - '
                  '%(levelname)s - %(message)s')
logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format=LOGGING_FORMAT,
                    datefmt='%m/%d/%Y %H:%M:%S')
LOGGER = logging.getLogger(__name__)


class DcosRestorer():

    def __init__(self, url, filePath, service):
        endpointMap = {'marathon': '/v2/apps',
                       'metronome': '/v0/scheduled-jobs'}
        self.url = url + endpointMap[service]
        self.file = filePath
        self.service = service

    def loadFile(self):
        LOGGER.info('Loading file %s', self.file)
        return json.load(open(self.file))

    def registerConfig(self, config):
        LOGGER.info('Restoring %s', config['id'])
        if self.service == 'marathon':
            if config.get('uris'):
                del config['uris']
        r = requests.post(self.url, json=config)
        LOGGER.info('Status code: %s', str(r.status_code))
        LOGGER.info('Body: %s', r.text)

    def run(self):
        configs = self.loadFile()
        if self.service == 'marathon':
            configs = configs['apps']
        for config in configs:
            self.registerConfig(config)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Restore DCOS cluster')
    parser.add_argument(
        '--url', help='the url for the service\'s API', default='http://localhost:8080')
    parser.add_argument(
        '--filePath', help='the backup file to restore', default='backup.json')
    parser.add_argument(
        'service', help='service to restore', choices=['marathon', 'metronome'])
    args = parser.parse_args()
    restorer = DcosRestorer(args.url, args.filePath, args.service)
    restorer.run()
