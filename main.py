#!/usr/bin/python

###############################################
# Export the following environment variables: #
# AWS_ACCESS_KEY_ID                           #
# AWS_SECRET_ACCESS_KEY                       #
# AWS_DEFAULT_REGION                          #
###############################################

from datetime import date
from apscheduler.schedulers.background import BlockingScheduler

import argparse
import logging
import io
import json
import os
import sys

import boto3
import requests

LOGGING_FORMAT = ('%(asctime)s - %(name)s - %(threadName)s - '
                  '%(levelname)s - %(message)s')
logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format=LOGGING_FORMAT,
                    datefmt='%m/%d/%Y %H:%M:%S')
LOGGER = logging.getLogger(__name__)
scheduler = BlockingScheduler({'apscheduler.timezone': 'UTC'})


class DcosBackuper():

    def __init__(self, bucket=None, environment=None, metricNameSpace=None,
                 marathonUrl=None, metronomeUrl=None, alarmTopic=None, scheduledBkpHour=None):
        self.s3_bucket = os.getenv("AWS_BUCKET", bucket)
        self.environment = os.getenv("BKP_ENVIRONMENT", environment)
        self.marathonUrl = os.getenv("MARARTHON_URL", marathonUrl)
        self.metronomeUrl = os.getenv("METRONOME_URL", metronomeUrl)
        self.metricNameSpace = os.getenv(
            "AWS_METRIC_NAMESPACE", metricNameSpace)
        self.alarmTopic = os.getenv("AWS_ALARM_TOPIC", alarmTopic)
        self.scheduledBkpHour = os.getenv("SCHEDULED_BKP_HOUR", scheduledBkpHour)

    def getConfig(self, url, path):
        endpoint = url + path
        r = requests.get(endpoint)
        if r.status_code != 200:
            LOGGER.error('Request ' + endpoint +
                         ' failed with status ' + str(r.status_code))
            return
        else:
            return r.json()

    def getMarathonConfig(self):
        # master.mesos:8080
        return self.getConfig(self.marathonUrl, '/v2/apps')

    def getMetronomeConfig(self):
        # master.mesos:9000
        return self.getConfig(self.metronomeUrl, '/v1/jobs')

    def saveObjectToS3(self, obj, name):
        key = '{}/{}/{}'.format(self.environment, name,
                                date.today().isoformat())
        LOGGER.info('Saving %s', key)
        s3 = boto3.client('s3')
        s3.upload_fileobj(io.BytesIO(bytes(obj, "utf-8")), self.s3_bucket, key)

    def reportBackupSuccess(self, metricName):
        cloudwatch = boto3.client('cloudwatch')
        metricData = [{'MetricName': metricName,
                       'Value': 1,
                       'Unit': 'Count',
                       'Dimensions': [
                           {
                               'Name': 'EnvironmentBackup',
                               'Value': self.environment
                           }
                       ]
                      }]
        response = cloudwatch.put_metric_data(
            Namespace=self.metricNameSpace, MetricData=metricData)
        LOGGER.info(response)

    def createAlarm(self, service):
        cloudwatch = boto3.client('cloudwatch')

        alarm_name = '_QuintoAndar_Monitor_DCOS_BACKUP_%s_%s' % (
            self.environment, service)
        response = cloudwatch.put_metric_alarm(
            AlarmName=alarm_name,
            ComparisonOperator='LessThanThreshold',
            EvaluationPeriods=1,
            MetricName=service,
            Namespace=self.metricNameSpace,
            Period=86400,
            Statistic='Average',
            Threshold=1,
            ActionsEnabled=True,
            AlarmActions=[self.alarmTopic],
            OKActions=[self.alarmTopic],
            AlarmDescription='Alarm when %s %s %s' % (
                service, 'LessThanThreshold', 1),
            Dimensions=[
                {
                    'Name': 'EnvironmentBackup',
                    'Value': self.environment
                },
            ],
            TreatMissingData='breaching',
            Unit='Count'
        )
        LOGGER.info(response)

    def createAlarms(self, services):
        for service in services:
            self.createAlarm(service)

    def start(self):
        scheduler.add_job(self.run, 'cron',
                          hour=self.scheduledBkpHour, id='dcosBackuper')
        print(
            'Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            pass

    def run(self):
        self.saveObjectToS3(json.dumps(
            self.getMetronomeConfig()), 'metronome')
        self.reportBackupSuccess('metronome')
        self.saveObjectToS3(json.dumps(
            self.getMarathonConfig()), 'marathon')
        self.reportBackupSuccess('marathon')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Backup DCOS cluster')
    parser.add_argument(
        '--marathonUrl', help='the url for marathon\'s API', default='http://master.mesos:8080')
    parser.add_argument(
        '--metronomeUrl', help='the url for metronome\'s API', default='http://master.mesos:9000')
    parser.add_argument(
        '--environment', help='the backedup environment', default='test')
    parser.add_argument(
        '--bucket', help='the backup bucket', default='test')
    parser.add_argument(
        '--metricNameSpace', help='the CloudWatch Metric Namespace', default='DCOSServices')
    parser.add_argument(
        '--topicAlarm', help='the topic to send alarms to')
    parser.add_argument(
        '--scheduledBkpHour', help='the hour of the day for the schedule the service to run',
        default=None)
    args = parser.parse_args()

    dcosBackuper = DcosBackuper(environment=args.environment, marathonUrl=args.marathonUrl,
                                metronomeUrl=args.metronomeUrl,
                                metricNameSpace=args.metricNameSpace,
                                alarmTopic=args.topicAlarm, scheduledBkpHour=args.scheduledBkpHour)

    if dcosBackuper.alarmTopic != None:
        dcosBackuper.createAlarms(['marathon', 'metronome'])

    if dcosBackuper.scheduledBkpHour != None:
        dcosBackuper.start()
    else:
        dcosBackuper.run()


# TODO: also backup zookeeper: https://github.com/mhausenblas/burry.sh
