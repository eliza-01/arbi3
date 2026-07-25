from fastapi import Depends, HTTPException

from app.api.dependencies import get_container
from app.container import Container
from app.db.session import SessionFactory
from app.services.spreads.pairs import normalize_exchange_pair


async def delete_favorite(
    asset_id: int,
    exchange_a: str,
    exchange_b: str,
    container: Container = Depends(get_container),
) -> dict:
    asset = container.catalog.get(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    try:
        left, right = normalize_exchange_pair(exchange_a.lower(), exchange_b.lower())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if left not in asset.exchange_ids or right not in asset.exchange_ids:
        raise HTTPException(status_code=404, detail="Exchange pair is not available for asset")

    async with SessionFactory() as session:
        await container.favorite_pair_repository.remove(
            session,
            asset_id=asset_id,
            exchange_a_id=asset.exchange_ids[left],
            exchange_b_id=asset.exchange_ids[right],
        )
        await session.commit()
        favorite_pairs = await container.favorite_pair_repository.list_keys(session)
    await container.runtime.set_favorites(favorite_pairs)
    return {
        "asset_id": asset_id,
        "exchange_a": left,
        "exchange_b": right,
        "is_favorite": False,
    }
