"""Turn a raw marktguru offer dict into a flat, stored-friendly record."""
from dataclasses import dataclass, fields

from .categories import classify
from .config import IMAGE_CDN


@dataclass
class Offer:
    id: int
    retailer: str
    retailer_key: str
    product_name: str
    brand: str | None
    category: str | None
    category_group: str
    description: str | None
    price: float | None
    old_price: float | None
    discount_pct: float | None
    reference_price: float | None
    unit: str | None
    volume: float | None
    valid_from: str | None
    valid_to: str | None
    image_url: str | None
    scraped_at: str


COLUMNS = [f.name for f in fields(Offer)]


def _first(seq):
    return seq[0] if seq else None


def normalize(raw, scraped_at):
    """Map a raw API offer to an Offer, or None if it has no usable id."""
    oid = raw.get("id")
    if oid is None:
        return None

    advertiser = _first(raw.get("advertisers") or []) or {}
    brand = raw.get("brand") or {}
    category = _first(raw.get("categories") or []) or {}
    product = raw.get("product") or {}
    unit = raw.get("unit") or {}
    validity = _first(raw.get("validityDates") or []) or {}

    price = raw.get("price")
    old_price = raw.get("oldPrice")
    discount_pct = None
    if price is not None and old_price and old_price > 0 and price < old_price:
        discount_pct = round((1 - price / old_price) * 100, 1)

    has_image = (raw.get("images") or {}).get("count")
    image_url = IMAGE_CDN.format(id=oid, size="medium") if has_image else None

    name = (
        product.get("name")
        or brand.get("name")
        or raw.get("description")
        or "Unbekanntes Produkt"
    )
    category_name = category.get("name")

    return Offer(
        id=oid,
        retailer=advertiser.get("name") or "?",
        retailer_key=advertiser.get("uniqueName") or "",
        product_name=name,
        brand=brand.get("name"),
        category=category_name,
        category_group=classify(category_name),
        description=raw.get("description"),
        price=price,
        old_price=old_price,
        discount_pct=discount_pct,
        reference_price=raw.get("referencePrice"),
        unit=unit.get("shortName"),
        volume=raw.get("volume"),
        valid_from=validity.get("from"),
        valid_to=validity.get("to"),
        image_url=image_url,
        scraped_at=scraped_at,
    )
