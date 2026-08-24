import uuid
import json
import aio_pika
from app.core.redis import redis_client
from app.core.mq import get_mq_channel, QUEUE_NAME

# Atomic check and decrement script
LUA_RESERVE_SCRIPT = """
local stock_key = KEYS[1]
local reserved_set = KEYS[2]
local req_qty = tonumber(ARGV[1])
local user_id = ARGV[2]
local reservation_id = ARGV[3]

local current_stock = tonumber(redis.call('get', stock_key) or 0)

if current_stock >= req_qty then
    redis.call('decrby', stock_key, req_qty)
    redis.call('hset', reserved_set, reservation_id, req_qty)
    return reservation_id
else
    return "OUT_OF_STOCK"
end
"""

class InventoryService:
    @staticmethod
    async def initialize_product(product_id: str, total_stock: int):
        await redis_client.set(f"stock:{product_id}", total_stock)

    @staticmethod
    async def reserve_stock(product_id: str, user_id: str, quantity: int, idempotency_key: str):
        # Check idempotency first in Redis
        cached_res = await redis_client.get(f"idempotency:{idempotency_key}")
        if cached_res:
            return json.loads(cached_res)

        reservation_id = str(uuid.uuid4())
        stock_key = f"stock:{product_id}"
        reserved_set = f"reserved:{product_id}"

        # Execute atomic Lua script
        result = await redis_client.eval(
            LUA_RESERVE_SCRIPT,
            2,
            stock_key,
            reserved_set,
            quantity,
            user_id,
            reservation_id
        )

        if result == "OUT_OF_STOCK":
            return {"status": "FAILED", "reason": "OUT_OF_STOCK"}

        # Publish order to RabbitMQ
        order_event = {
            "reservation_id": reservation_id,
            "idempotency_key": idempotency_key,
            "product_id": product_id,
            "user_id": user_id,
            "quantity": quantity
        }

        conn, channel = await get_mq_channel()
        async with conn:
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(order_event).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=QUEUE_NAME
            )

        response = {"status": "RESERVED", "reservation_id": reservation_id}
        await redis_client.setex(f"idempotency:{idempotency_key}", 3600, json.dumps(response))
        return response