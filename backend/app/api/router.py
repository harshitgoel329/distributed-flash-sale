from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from app.services.inventory import InventoryService

api_router = APIRouter(prefix="/api/v1")

class InitProductReq(BaseModel):
    product_id: str
    stock: int

class ReservationReq(BaseModel):
    product_id: str
    user_id: str
    quantity: int

@api_router.post("/products/init")
async def init_product(req: InitProductReq):
    await InventoryService.initialize_product(req.product_id, req.stock)
    return {"status": "SUCCESS", "message": f"Stock set to {req.stock}"}

@api_router.post("/orders/reserve")
async def reserve_item(req: ReservationReq, x_idempotency_key: str = Header(...)):
    res = await InventoryService.reserve_stock(
        product_id=req.product_id,
        user_id=req.user_id,
        quantity=req.quantity,
        idempotency_key=x_idempotency_key
    )
    if res.get("status") == "FAILED":
        raise HTTPException(status_code=409, detail="Item is out of stock")
    return res