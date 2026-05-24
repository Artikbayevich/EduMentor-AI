import asyncio
from sqlalchemy import select
from core.database import AsyncSessionLocal
from models.user import User

async def run():
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.hemis_id == 'admin_hemis'))).scalar_one()
        print('User tg:', user.telegram_id)

if __name__ == "__main__":
    asyncio.run(run())
