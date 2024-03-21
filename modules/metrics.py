import enum

import prometheus_client


class Metrics(enum.Enum):
    URL_COUNT = (
        "url_count",
        "Number of urls in the database",
        prometheus_client.Counter,
    )
    QUERY_TIME = (
        "query_time",
        "Time taken to execute SQLite queries",
        prometheus_client.Summary,
        ["query_type"],
    )
    HTTP_CODE = (
        "http_code",
        "Count of each HTTP Response code",
        prometheus_client.Counter,
        ['path', 'code'],
    )
    USED_ALIAS_QUEUE_SIZE = (
        "used_alias_queue_size",
        "Size of the used alias queue",
        prometheus_client.Gauge,
    )

    def __init__(self, title, description, prometheus_type, labels=()):
        # we use the above default value for labels because it matches what's used
        # in the prometheus_client library's metrics constructor, see
        # https://github.com/prometheus/client_python/blob/fd4da6cde36a1c278070cf18b4b9f72956774b05/prometheus_client/metrics.py#L115
        self.title = title
        self.description = description
        self.prometheus_type = prometheus_type
        self.labels = labels


class MetricsHandler:
    _instance = None

    def __init__(self):
        raise RuntimeError('Call MetricsHandler.instance() instead')

    def init(self) -> None:
        for metric in Metrics:
            setattr(
                self,
                metric.title,
                metric.prometheus_type(
                    metric.title, metric.description, labelnames=metric.labels
                ),
            )

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
            cls.init(cls)
        return cls._instance
