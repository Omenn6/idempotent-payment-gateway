class MetricsTracker:
    def __init__(self):
        self._retry_count = 0

    def increment_retry_counter(self) -> None:
        self._retry_count += 1

    @property
    def retry_count(self) -> int:
        return self._retry_count


metrics = MetricsTracker()
