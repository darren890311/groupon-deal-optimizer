import json
import re
from typing import Any

from bs4 import BeautifulSoup


def _text(el) -> str | None:
    if el is None:
        return None
    t = el.get_text(" ", strip=True)
    return t or None


def _money(s: Any) -> float | None:
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    m = re.search(r"\$?\s*(\d{1,5}(?:[.,]\d{1,2})?)", str(s).replace(",", ""))
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _collect_jsonld(soup: BeautifulSoup) -> list[dict[str, Any]]:
    blocks = []
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.text or ""
        if not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            if isinstance(item.get("@graph"), list):
                blocks.extend(d for d in item["@graph"] if isinstance(d, dict))
            else:
                blocks.append(item)
    return blocks


def _find_jsonld(blocks: list[dict[str, Any]], type_name: str) -> dict[str, Any] | None:
    for b in blocks:
        t = b.get("@type")
        if t == type_name or (isinstance(t, list) and type_name in t):
            return b
    return None


def _find_business(blocks: list[dict[str, Any]]) -> dict[str, Any] | None:
    business_types = {
        "HealthAndBeautyBusiness", "BeautySalon", "DaySpa", "AutoRepair",
        "Restaurant", "TouristAttraction", "LocalBusiness", "Store",
        "MedicalBusiness", "Dentist", "Optician",
    }
    for b in blocks:
        t = b.get("@type")
        if t in business_types or (isinstance(t, list) and any(x in business_types for x in t)):
            return b
    return None


def _extract_breadcrumbs(blocks: list[dict[str, Any]]) -> list[str]:
    bc = _find_jsonld(blocks, "BreadcrumbList")
    if not bc or not isinstance(bc.get("itemListElement"), list):
        return []
    crumbs: list[str] = []
    for item in bc["itemListElement"]:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not name and isinstance(item.get("item"), dict):
            name = item["item"].get("name")
        if name:
            crumbs.append(name)
    return crumbs


def _extract_prices_from_variants(variants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for v in variants:
        if not isinstance(v, dict):
            continue
        offer = v.get("offers")
        if isinstance(offer, list):
            offer = offer[0] if offer else {}
        if not isinstance(offer, dict):
            continue
        list_price = _money(offer.get("price"))
        deal_price = list_price
        spec = offer.get("priceSpecification")
        if isinstance(spec, dict):
            sale = _money(spec.get("price"))
            if sale is not None:
                price_type = (spec.get("priceType") or "").lower()
                if "saleprice" in price_type or sale < (list_price or 0):
                    deal_price = sale
        discount_pct = None
        if list_price and deal_price and list_price > 0 and deal_price < list_price:
            discount_pct = round((1 - deal_price / list_price) * 100, 1)
        out.append({
            "label": v.get("name") or "Default",
            "original_price": list_price,
            "deal_price": deal_price,
            "discount_pct": discount_pct,
        })
    return out


def _extract_address(business: dict[str, Any] | None) -> tuple[str | None, str | None, str | None]:
    if not business:
        return None, None, None
    addr = business.get("address")
    if not isinstance(addr, dict):
        return None, None, None
    street = addr.get("streetAddress")
    locality = addr.get("addressLocality")
    region = addr.get("addressRegion")

    city: str | None = None
    if street and isinstance(street, str):
        m = re.search(r",\s*([A-Z][A-Za-z .'-]{2,40})\s*$", street.strip())
        if m:
            city = m.group(1).strip()
    if not city and locality and not _looks_like_venue_name(locality):
        city = locality
    return city, region, street


def _looks_like_venue_name(s: str) -> bool:
    if not s:
        return False
    venue_words = ("hotel", "mall", "plaza", "center", "centre", "square", "tower", "building")
    sl = s.lower()
    return any(w in sl for w in venue_words)


def _extract_faqs(blocks: list[dict[str, Any]]) -> list[dict[str, str]]:
    faq = _find_jsonld(blocks, "FAQPage")
    if not faq or not isinstance(faq.get("mainEntity"), list):
        return []
    out = []
    for q in faq["mainEntity"]:
        if not isinstance(q, dict):
            continue
        question = q.get("name")
        ans = q.get("acceptedAnswer") or {}
        answer = ans.get("text") if isinstance(ans, dict) else None
        if question and answer:
            out.append({"question": question, "answer": answer})
    return out[:20]


def parse_audit(html: str, url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    blocks = _collect_jsonld(soup)

    product = (
        _find_jsonld(blocks, "ProductGroup")
        or _find_jsonld(blocks, "Product")
        or {}
    )
    business = _find_business(blocks)

    title = (
        product.get("name")
        or _text(soup.select_one("h1"))
        or (soup.find("meta", property="og:title") or {}).get("content")
    )
    h1 = soup.select_one("h1")
    subtitle = None
    if h1:
        sib = h1.find_next_sibling()
        if sib:
            subtitle = _text(sib)

    merchant = None
    brand = product.get("brand")
    if isinstance(brand, dict):
        merchant = brand.get("name")
    elif isinstance(brand, str):
        merchant = brand
    if not merchant and business:
        merchant = business.get("name")

    description = product.get("description") or (
        (soup.find("meta", attrs={"name": "description"}) or {}).get("content")
    )

    variants = product.get("hasVariant") or []
    prices = _extract_prices_from_variants(variants if isinstance(variants, list) else [])
    if not prices and isinstance(product.get("offers"), (dict, list)):
        offer = product["offers"]
        if isinstance(offer, list):
            offer = offer[0] if offer else {}
        if isinstance(offer, dict):
            list_price = _money(offer.get("price"))
            spec = offer.get("priceSpecification") or {}
            deal_price = _money(spec.get("price")) if isinstance(spec, dict) else None
            discount_pct = None
            if list_price and deal_price and list_price > 0 and deal_price < list_price:
                discount_pct = round((1 - deal_price / list_price) * 100, 1)
            prices = [{
                "label": offer.get("name") or "Default",
                "original_price": list_price,
                "deal_price": deal_price or list_price,
                "discount_pct": discount_pct,
            }]

    aggregate = product.get("aggregateRating") or {}
    if not aggregate and business:
        aggregate = business.get("aggregateRating") or {}
    rating = None
    review_count = None
    if isinstance(aggregate, dict):
        try:
            rv = aggregate.get("ratingValue")
            rating = float(rv) if rv is not None else None
        except (TypeError, ValueError):
            pass
        try:
            rc = aggregate.get("reviewCount") or aggregate.get("ratingCount")
            review_count = int(rc) if rc is not None else None
        except (TypeError, ValueError):
            pass

    review_list = product.get("reviews") or product.get("review") or []
    reviews_out: list[dict[str, Any]] = []
    if isinstance(review_list, list):
        for r in review_list[:10]:
            if not isinstance(r, dict):
                continue
            rating_val = None
            rr = r.get("reviewRating")
            if isinstance(rr, dict):
                try:
                    rating_val = float(rr.get("ratingValue")) if rr.get("ratingValue") is not None else None
                except (TypeError, ValueError):
                    pass
            author = r.get("author")
            if isinstance(author, dict):
                author = author.get("name")
            reviews_out.append({
                "rating": rating_val,
                "quote": r.get("reviewBody") or r.get("description"),
                "author": author,
                "date": r.get("datePublished"),
            })

    crumbs = _extract_breadcrumbs(blocks)
    category = " > ".join(crumbs) if crumbs else None

    city, region, street = _extract_address(business)

    faqs = _extract_faqs(blocks)
    highlights = _extract_highlights(soup)
    fine_print = _extract_fine_print(soup)

    bought_label = None
    body_text = soup.get_text(" ", strip=True)
    bought_match = re.search(r"([\d,]+\+?\s*bought)", body_text, re.IGNORECASE)
    if bought_match:
        bought_label = bought_match.group(1)

    images = soup.find_all("img")
    image_count = sum(1 for img in images if img.get("src") or img.get("data-src"))

    h1s = [_text(h) for h in soup.find_all("h1") if _text(h)]
    h2s = [_text(h) for h in soup.find_all("h2") if _text(h)][:25]
    meta_title = _text(soup.find("title"))
    meta_desc = (soup.find("meta", attrs={"name": "description"}) or {}).get("content")

    body_lower = body_text.lower()
    urgency_signals = [
        kw for kw in ["selling fast", "limited time", "almost gone", "ends soon", "only a few left", "limited supply"]
        if kw in body_lower
    ]
    trust_signals = {
        "has_rating": rating is not None,
        "has_review_count": review_count is not None,
        "has_bought_label": bought_label is not None,
        "has_guarantee_text": "groupon guarantee" in body_lower or "money back" in body_lower,
    }

    return {
        "url": url,
        "title": title,
        "subtitle": subtitle,
        "merchant_name": merchant,
        "category": category,
        "breadcrumbs": crumbs,
        "city": city,
        "region": region,
        "address": street,
        "description": description,
        "highlights": highlights,
        "fine_print": fine_print,
        "prices": prices,
        "rating": rating,
        "review_count": review_count,
        "bought_label": bought_label,
        "reviews": reviews_out,
        "faqs": faqs,
        "image_count": image_count,
        "seo": {
            "meta_title": meta_title,
            "meta_description": meta_desc,
            "h1": h1s,
            "h2": h2s,
        },
        "urgency_signals": urgency_signals,
        "trust_signals": trust_signals,
    }


def _extract_highlights(soup: BeautifulSoup) -> list[str]:
    candidates: list[str] = []
    for header in soup.find_all(["h2", "h3", "h4"]):
        label = _text(header) or ""
        if re.search(r"highlight|what you get|what's included|the deal", label, re.IGNORECASE):
            ul = header.find_next("ul")
            if ul and _is_content_list(ul):
                items = [_text(li) for li in ul.find_all("li")]
                items = [t for t in items if t]
                if items:
                    candidates.extend(items)
                    break
    if not candidates:
        for ul in soup.find_all("ul"):
            if not _is_content_list(ul):
                continue
            items = [_text(li) for li in ul.find_all("li")]
            items = [t for t in items if t and 8 < len(t) < 250]
            if 2 <= len(items) <= 12:
                candidates = items
                break
    return candidates[:15]


def _is_content_list(ul) -> bool:
    """Reject obvious nav/breadcrumb/tab lists."""
    text = (ul.get("class") and " ".join(ul.get("class")).lower()) or ""
    if any(bad in text for bad in ("nav", "breadcrumb", "tab", "menu", "header", "footer")):
        return False
    parent = ul.parent
    while parent is not None and getattr(parent, "name", None):
        cls = parent.get("class") if hasattr(parent, "get") else None
        if cls:
            joined = " ".join(cls).lower()
            if any(bad in joined for bad in ("nav", "header", "footer", "tab")):
                return False
        if parent.name in ("nav", "header", "footer"):
            return False
        parent = parent.parent
    return True


def _extract_fine_print(soup: BeautifulSoup) -> str | None:
    for header in soup.find_all(["h2", "h3", "h4"]):
        label = _text(header) or ""
        if re.search(r"fine print|terms|conditions|need to know", label, re.IGNORECASE):
            sib = header.find_next_sibling()
            chunks: list[str] = []
            for _ in range(5):
                if sib is None:
                    break
                t = _text(sib)
                if t:
                    chunks.append(t)
                sib = sib.find_next_sibling()
            if chunks:
                return " ".join(chunks)[:3000]
    return None
