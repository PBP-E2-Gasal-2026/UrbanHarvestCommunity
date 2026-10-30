class SearchError(Exception):
    code = "search_failed"


class InvalidSearch(SearchError):
    code = "invalid_search"


class UnsafeSearch(InvalidSearch):
    code = "unsafe_search"


class MarketplaceUnavailable(SearchError):
    code = "marketplace_unavailable"


class ProviderUnavailable(SearchError):
    code = "provider_unavailable"


class QueueFull(SearchError):
    code = "queue_full"


class RateLimited(SearchError):
    code = "rate_limited"

    def __init__(self, retry_after):
        self.retry_after = retry_after
        super().__init__("Maksimal 5 pencarian per menit. Silakan coba lagi sebentar.")
