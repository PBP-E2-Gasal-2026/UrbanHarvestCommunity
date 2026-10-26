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
