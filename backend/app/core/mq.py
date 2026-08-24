import aio_pika
from app.core.config import settings

QUEUE_NAME = "order_processing_queue"

async def get_mq_channel():
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    await channel.declare_queue(QUEUE_NAME, durable=True)
    return connection, channel