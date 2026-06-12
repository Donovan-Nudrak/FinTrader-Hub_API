from sqlalchemy.orm import Session

from core.exceptions import ConflictError, NotFoundError, ValidationError
from modules.asset.models.asset import Asset
from modules.asset.repositories import AssetRepository
from modules.asset.schemas import AssetResponse, CreateAssetRequest, UpdateAssetRequest


class AssetService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.asset_repository = AssetRepository(db)

    def create_asset(self, request: CreateAssetRequest) -> AssetResponse:
        symbol = request.symbol.strip().upper()

        if self.asset_repository.symbol_exists(symbol):
            raise ConflictError("Asset symbol already exists", code="SYMBOL_EXISTS")

        asset = Asset(
            symbol=symbol,
            external_id=request.external_id,
            name=request.name.strip(),
            market=request.market,
            asset_type=request.asset_type,
            currency=request.currency.upper(),
            is_active=True,
        )
        created = self.asset_repository.create(asset)
        self.db.commit()
        return AssetResponse.model_validate(created)

    def update_asset(self, asset_id: int, request: UpdateAssetRequest) -> AssetResponse:
        asset = self._get_asset(asset_id)
        update_data = request.model_dump(exclude_unset=True)

        if not update_data:
            raise ValidationError("No fields provided for update")

        if "symbol" in update_data and update_data["symbol"] is not None:
            symbol = update_data["symbol"].strip().upper()
            if self.asset_repository.symbol_exists(symbol, exclude_id=asset.id):
                raise ConflictError("Asset symbol already exists", code="SYMBOL_EXISTS")
            asset.symbol = symbol

        if "external_id" in update_data:
            asset.external_id = update_data["external_id"]

        if "name" in update_data and update_data["name"] is not None:
            asset.name = update_data["name"].strip()

        if "market" in update_data and update_data["market"] is not None:
            asset.market = update_data["market"]

        if "asset_type" in update_data and update_data["asset_type"] is not None:
            asset.asset_type = update_data["asset_type"]

        if "currency" in update_data and update_data["currency"] is not None:
            asset.currency = update_data["currency"].upper()

        if "is_active" in update_data and update_data["is_active"] is not None:
            asset.is_active = update_data["is_active"]

        updated = self.asset_repository.update(asset)
        self.db.commit()
        return AssetResponse.model_validate(updated)

    def search_assets(self, *, symbol: str | None = None, name: str | None = None) -> list[AssetResponse]:
        if not symbol and not name:
            raise ValidationError("At least one search parameter is required: symbol or name")

        assets = self.asset_repository.search(symbol=symbol, name=name)
        return [AssetResponse.model_validate(asset) for asset in assets]

    def list_assets(self) -> list[AssetResponse]:
        assets = self.asset_repository.list_all()
        return [AssetResponse.model_validate(asset) for asset in assets]

    def _get_asset(self, asset_id: int) -> Asset:
        asset = self.asset_repository.get_by_id(asset_id)
        if asset is None:
            raise NotFoundError("Asset not found")
        return asset
