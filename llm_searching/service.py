"""Search orchestration; only database facts become user-visible product claims."""

from .exceptions import InvalidSearch, ProviderUnavailable
from .filters import normalize_category_filters, parse_filters, validate_prompt
from .marketplace import MarketplaceRepository
from .openrouter import OpenRouterClient

CLARIFY = "Produk yang sesuai belum ditemukan. Perjelas nama produk, lokasi, atau rentang harga yang Anda inginkan."


class SearchService:
    def __init__(self, repository=None, client=None):
        self.repository = repository or MarketplaceRepository()
        self.client = client or OpenRouterClient()

    def run(self, prompt):
        prompt = validate_prompt(prompt)
        category_slugs = self.repository.category_slugs()
        extraction = self.client.extract(prompt, category_slugs)
        if not isinstance(extraction, dict) or set(extraction) != {
            "status",
            "filters",
            "clarification",
            "unsupported_conditions",
        }:
            raise InvalidSearch("Respons interpretasi tidak sesuai skema.")
        if extraction["status"] not in (
            "search",
            "needs_clarification",
        ) or not isinstance(extraction["clarification"], str):
            raise InvalidSearch("Status interpretasi tidak valid.")
        unsupported = extraction["unsupported_conditions"]
        if (
            not isinstance(unsupported, list)
            or len(unsupported) > 20
            or any(not isinstance(x, str) or len(x) > 300 for x in unsupported)
        ):
            raise InvalidSearch("Kondisi pencarian tidak valid.")
        if extraction["status"] == "needs_clarification" or unsupported:
            return {
                "status": "needs_clarification",
                "filters": {},
                "products": [],
                "degraded": False,
                "explanation": "Mohon perjelas pencarian menggunakan nama produk, kategori, harga per satuan, lokasi, atau stok. Sebagian kriteria belum didukung.",
            }
        filters = normalize_category_filters(
            parse_filters(extraction["filters"]), category_slugs
        )
        candidates = self.repository.search(filters)
        if not candidates:
            return {
                "status": "needs_clarification",
                "filters": filters.to_dict(),
                "products": [],
                "explanation": CLARIFY,
                "degraded": False,
            }
        try:
            suggestions = self.client.suggest(prompt, filters, candidates)
            selected = self._ground(suggestions, candidates, filters)
            degraded = False
        except (InvalidSearch, ProviderUnavailable):
            selected = [(card, []) for card in candidates]
            degraded = True
        if filters.sort in ("price_asc", "price_desc"):
            # Price ordering comes from the database. Model ranking must neither
            # reorder it nor hide the cheapest/most expensive matching candidate.
            reasons_by_id = {card.id: reasons for card, reasons in selected}
            selected = [(card, reasons_by_id.get(card.id, [])) for card in candidates]
        explanations = []
        if filters.sort == "price_asc":
            explanations.append(
                "Produk sesuai pencarian, diurutkan berdasarkan harga tercantum dari yang termurah."
            )
        elif filters.sort == "price_desc":
            explanations.append(
                "Produk sesuai pencarian, diurutkan berdasarkan harga tercantum dari yang tertinggi."
            )
        for card, reasons in selected:
            price = f"{card.price:,}".replace(",", ".")
            sentence = f"{card.name}: Rp{price}/{card.unit}, lokasi {card.location}, stok {card.stock}."
            if "within_budget" in reasons:
                sentence += " Harga sesuai batas pencarian."
            if "matches_location" in reasons:
                sentence += " Lokasi sesuai pencarian."
            if "available" in reasons:
                sentence += " Stok tersedia."
            explanations.append(sentence)
        if degraded:
            explanations.insert(
                0,
                "Suggestion AI belum tersedia; berikut produk hasil filter pencarian.",
            )
        return {
            "status": "succeeded",
            "filters": filters.to_dict(),
            "products": [c.to_dict() for c, _ in selected],
            "explanation": "\n".join(explanations),
            "degraded": degraded,
        }

    def _ground(self, payload, candidates, filters):
        if not isinstance(payload, dict) or set(payload) != {"suggestions"}:
            raise InvalidSearch("Suggestion tidak valid.")
        suggestions = payload["suggestions"]
        if not isinstance(suggestions, list) or not 1 <= len(suggestions) <= len(
            candidates
        ):
            raise InvalidSearch("Suggestion tidak valid.")
        by_id = {c.id: c for c in candidates}
        selected, seen = [], set()
        for suggestion in suggestions:
            if not isinstance(suggestion, dict) or set(suggestion) != {"id", "reasons"}:
                raise InvalidSearch("Suggestion tidak valid.")
            ident, reasons = suggestion["id"], suggestion["reasons"]
            if (
                type(ident) is not int
                or ident not in by_id
                or ident in seen
                or not isinstance(reasons, list)
                or len(reasons) > 4
            ):
                raise InvalidSearch("Produk suggestion bukan kandidat yang valid.")
            card = by_id[ident]
            evidence = {
                "within_budget": (
                    filters.min_price is not None or filters.max_price is not None
                )
                and (filters.min_price is None or card.price >= filters.min_price)
                and (filters.max_price is None or card.price <= filters.max_price),
                "matches_location": bool(filters.location)
                and filters.location.casefold() in card.location.casefold(),
                "available": card.is_available and card.stock > 0,
                "matches_keyword": bool(filters.keyword)
                and filters.keyword.casefold()
                in (card.name + " " + card.description).casefold(),
            }
            if any(
                not isinstance(reason, str) or not evidence.get(reason, False)
                for reason in reasons
            ):
                raise InvalidSearch("Alasan suggestion tidak didukung fakta produk.")
            seen.add(ident)
            selected.append((card, reasons))
        return selected
