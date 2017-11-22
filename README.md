# DCOS Backuper

Backsup Marathon and Metronome frameworks from DCOS.

## Configuration

 |      Command      |        Env Var        | Description
 | ----------------- | --------------------- | -----------
 | --marathonUrl     | MARARTHON_URL         | Marathon URL
 | --metronomeUrl    | METRONOME_URL         | Metronome URL
 | --environment     | BKP_ENVIRONMENT       | Backup Environment Name
 | --bucket          | AWS_BUCKET            | AWS Bucket to save Backup
 | --metricNameSpace | AWS_METRIC_NAMESPACE  | AWS Metric Namespace to report backup success
 | --topicAlarm      | AWS_ALARM_TOPIC       | AWS alarm topic to alert backup failure
 | --schedule        | SCHEDULED_BKP_HOUR    | The hour of the day for the backup to run
 |                   | AWS_ACCESS_KEY_ID     | AWS key ID
 |                   | AWS_SECRET_ACCESS_KEY | AWS secret key
 |                   | AWS_DEFAULT_REGION    | AWS default region

 ## Extra features

 Creates an alarm on Cloudwatch to warn when daily backup fails.

 ## TODO

 - Backup zookeeper: https://github.com/mhausenblas/burry.sh

## Restoring

- Usage

```bash
./restore.py [marathon | metronome] <configs>
```

- Configuration

 |      Command      | Description
 | ----------------- | -----------
 | --url             | The framework's API URL
 | --file            | The backup file

- Tip

You can use an SSL tunnel to open the framework's API port.

```bash
ssh -L 8080:127.0.0.1:8080 <masterUser@masterHost>
```