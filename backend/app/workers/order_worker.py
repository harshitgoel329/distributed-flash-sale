import asyncio
import json
import aio_pika
from app.core.mq import QUEUE_NAME
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.schema import Order, OrderStatus
from app.core.redis import redis_client

async def get_robust_connection():
    """Retries connecting to RabbitMQ until it is ready."""
    while True:
        try:
            print(" [*] Connecting to RabbitMQ at", settings.RABBITMQ_URL)
            connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
            print(" [✔] Connected to RabbitMQ successfully.")
            return connection
        except Exception as e:
            print(f" [!] RabbitMQ not ready yet ({e}). Retrying in 3 seconds...")
            await asyncio.sleep(3)

async def process_orders():
    connection = await get_robust_connection()
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)
    queue = await channel.declare_queue(QUEUE_NAME, durable=True)

    print(" [*] Order persistence worker active. Awaiting tasks...")

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                try:
                    data = json.loads(message.body.decode())
                    async with AsyncSessionLocal() as session:
                        order = Order(
                            id=data["reservation_id"],
                            idempotency_key=data["idempotency_key"],
                            user_id=data["user_id"],
                            product_id=data["product_id"],
                            quantity=data["quantity"],
                            status=OrderStatus.CONFIRMED
                        )
                        session.add(order)
                        await session.commit()

                        # Publish state update via Redis Pub/Sub for WebSockets
                        await redis_client.publish(
                            "order_updates",
                            json.dumps({"order_id": order.id, "status": "CONFIRMED"})
                        )
                        print(f" [✔] Persisted and confirmed order: {order.id}")
                except Exception as e:
                    print(f" [!] Error processing order: {e}")

if __name__ == "__main__":
    asyncio.run(process_orders())