import asyncio
import asyncpg

async def create_db():
    conn = await asyncpg.connect(user="postgres", password="Akbarali_03", database="postgres", host="localhost")
    try:
        await conn.execute("CREATE DATABASE sezgi_db")
        print("Database sezgi_db created successfully.")
    except asyncpg.exceptions.DuplicateDatabaseError:
        print("Database sezgi_db already exists.")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_db())
