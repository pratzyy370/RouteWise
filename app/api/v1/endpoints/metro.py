"""
Metro discovery and route query endpoints.
"""

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import DbSession
from app.repositories.metro_repo import MetroRepository
from app.schemas.metro import MetroStationResponse, NearbyStationsResponse
from app.services.metro_service import MetroService

router = APIRouter(tags=["Metro"])


@router.get("/nearby", response_model=NearbyStationsResponse)
async def get_nearby_stations(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude"),
    radius_m: int = Query(1500, ge=100, le=10000, description="Search radius in metres"),
    limit: int = Query(5, ge=1, le=50, description="Max stations to return"),
    db: DbSession = None,
):
    """
    Find metro stations near geographic coordinates.
    Computes accurate geodesic distances using the Haversine formula (with documented
    PostGIS ST_DWithin / ST_Distance query equivalent for production).
    """
    results = await MetroService.get_nearby_stations(db, lat, lng, radius_m=radius_m, limit=limit)

    station_responses = []
    for item in results:
        st = item["station"]
        station_responses.append(
            MetroStationResponse(
                id=st.id,
                name=st.name,
                code=st.code,
                line=st.line,
                latitude=st.latitude,
                longitude=st.longitude,
                is_interchange=st.is_interchange,
                station_order=st.station_order,
                distance_m=item["distance_m"],
            )
        )

    return NearbyStationsResponse(
        stations=station_responses,
        search_lat=lat,
        search_lng=lng,
        search_radius_m=radius_m,
        count=len(station_responses),
    )


@router.get("/stations", response_model=list[MetroStationResponse])
async def list_stations(
    line: str | None = Query(None, description="Filter by line ('purple' or 'green')"),
    db: DbSession = None,
):
    """List all Namma Metro stations, optionally filtered by line."""
    if line:
        stations = await MetroRepository.get_stations_by_line(db, line.lower())
    else:
        stations = await MetroRepository.get_all_stations(db)

    return [
        MetroStationResponse(
            id=st.id,
            name=st.name,
            code=st.code,
            line=st.line,
            latitude=st.latitude,
            longitude=st.longitude,
            is_interchange=st.is_interchange,
            station_order=st.station_order,
            distance_m=None,
        )
        for st in stations
    ]


@router.get("/route")
async def get_metro_route(
    from_code: str = Query(..., description="Origin station code (e.g. 'IDN')"),
    to_code: str = Query(..., description="Destination station code (e.g. 'MGR')"),
    db: DbSession = None,
):
    """Calculate the metro transit journey between two stations."""
    route = await MetroService.find_metro_route(db, from_code.upper(), to_code.upper())
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both station codes not found in network",
        )

    orig_st = route["origin_station"]
    dest_st = route["dest_station"]
    interchange = route.get("interchange_station")

    return {
        "origin_station": orig_st.name,
        "origin_code": orig_st.code,
        "dest_station": dest_st.name,
        "dest_code": dest_st.code,
        "station_count": route["station_count"],
        "duration_minutes": route["duration_minutes"],
        "cost": float(route["cost"]),
        "has_interchange": route["has_interchange"],
        "interchange_station": interchange.name if interchange else None,
        "lines": route["lines"],
    }
