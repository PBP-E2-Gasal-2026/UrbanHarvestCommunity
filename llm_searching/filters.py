import unicodedata
from dataclasses import asdict, dataclass

from .exceptions import InvalidSearch, UnsafeSearch


@dataclass(frozen=True)
class SearchFilters:
    keyword: str = ""
    categories: tuple[str, ...] = ()
    min_price: int | None = None
    max_price: int | None = None
    location: str = ""
    in_stock: bool = False
    sort: str = "newest"
    limit: int = 20

    def to_dict(self):
        result = asdict(self)
        result["categories"] = list(self.categories)
        return result


def validate_prompt(value: object) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 2000:
        raise InvalidSearch("Tulis kebutuhan pencarian, maksimal 2.000 karakter.")
    if any(
        unicodedata.category(c).startswith("C") and c not in "\n\t\r" for c in value
    ):
        raise InvalidSearch("Prompt memuat karakter kontrol yang tidak diizinkan.")
    return value.strip()


def parse_filters(payload: dict) -> SearchFilters:
    if not isinstance(payload, dict):
        raise InvalidSearch("Filter harus berupa objek JSON.")
    allowed = set(SearchFilters.__dataclass_fields__)
    if set(payload) - allowed:
        raise UnsafeSearch("Filter memuat operasi atau field yang tidak diizinkan.")
    data = dict(payload)
    for key in ("keyword", "location"):
        value = data.get(key, "")
        if not isinstance(value, str) or len(value) > 150:
            raise InvalidSearch("Kata kunci/lokasi tidak valid.")
        data[key] = value.strip()
    categories = data.get("categories", [])
    if (
        not isinstance(categories, list)
        or len(categories) > 20
        or any(
            not isinstance(c, str) or not c.strip() or len(c) > 100 for c in categories
        )
    ):
        raise InvalidSearch("Kategori tidak valid.")
    data["categories"] = tuple(dict.fromkeys(c.strip() for c in categories))
    for key in ("min_price", "max_price"):
        value = data.get(key)
        if value is not None and (type(value) is not int or not 0 <= value <= 10**12):
            raise InvalidSearch("Harga harus berupa bilangan bulat nonnegatif.")
    if (
        data.get("min_price") is not None
        and data.get("max_price") is not None
        and data["min_price"] > data["max_price"]
    ):
        raise InvalidSearch("Rentang harga terbalik.")
    if type(data.get("limit", 20)) is not int or not 1 <= data.get("limit", 20) <= 50:
        raise InvalidSearch("Batas hasil harus 1–50.")
    if type(data.get("in_stock", False)) is not bool:
        raise InvalidSearch("Filter stok harus boolean.")
    if data.get("sort", "newest") not in ("newest", "price_asc", "price_desc"):
        raise InvalidSearch("Urutan tidak didukung.")
    if not (
        data["keyword"]
        or data["location"]
        or data["categories"]
        or data.get("min_price") is not None
        or data.get("max_price") is not None
        or data.get("in_stock")
    ):
        raise InvalidSearch(
            "Perjelas produk, lokasi, kategori, harga, atau stok yang dicari."
        )
    return SearchFilters(**data)
