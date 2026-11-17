"""Catalog facets, public config, and health models for v1 API."""

from typing import Literal
from pydantic import BaseModel, Field

from app.schemas.common import BaseResponse


class FacetCount(BaseModel):
    value: str
    count: int


class CatalogFacetsResponse(BaseModel):
    categories: list[FacetCount] = Field(default_factory=list)
    brands: list[FacetCount] = Field(default_factory=list)
    materials: list[FacetCount] = Field(default_factory=list)


class PageSizeDefaults(BaseModel):
    default_limit: int = 20
    max_limit: int = 100


class PublicConfigResponse(BaseModel):
    confidence_thresholds: dict[str, float]
    too_close_margin: float
    drift_threshold: float
    window_options: list[str]
    page_size_defaults: PageSizeDefaults


class DependencyStatus(BaseModel):
    index: Literal["ok", "down"]
    model: Literal["ok", "down"]


class HealthResponseV1(BaseResponse):
    status: Literal["ok", "degraded"]
    dependencies: DependencyStatus
