from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_USER_AGENT = "listing-tracker/0.1 (+https://github.com/hnhonnguyen/listing-tracker)"


@dataclass
class Pagination:
    url_template: str
    start_page: int = 1
    max_pages: int = 3


@dataclass
class Selectors:
    item: str
    title: str
    price: str
    url: str
    title_attr: str | None = None
    price_attr: str | None = None
    url_attr: str = "href"


@dataclass
class SiteConfig:
    name: str
    base_url: str
    pagination: Pagination
    selectors: Selectors
    currency: str = "USD"
    id_regex: str | None = None
    delay_seconds: float = 1.5
    timeout_seconds: int = 30
    user_agent: str = DEFAULT_USER_AGENT

    @classmethod
    def load(cls, path: str | Path) -> "SiteConfig":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        missing = [key for key in ("name", "base_url", "pagination", "selectors") if key not in data]
        if missing:
            raise ValueError(f"{path}: missing required keys: {', '.join(missing)}")
        return cls(
            name=data["name"],
            base_url=data["base_url"],
            pagination=Pagination(**data["pagination"]),
            selectors=Selectors(**data["selectors"]),
            currency=data.get("currency", "USD"),
            id_regex=data.get("id_regex"),
            delay_seconds=float(data.get("delay_seconds", 1.5)),
            timeout_seconds=int(data.get("timeout_seconds", 30)),
            user_agent=data.get("user_agent", DEFAULT_USER_AGENT),
        )
