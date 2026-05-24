import asyncio
from sqlalchemy import text
from core.database import AsyncSessionLocal
from models.user import User, P2PRequest, P2PMatch, Skill, SkillType
import uuid
import random

async def seed_db():
    async with AsyncSessionLocal() as session:
        # Check if users already exist
        res = await session.execute(text("SELECT COUNT(id) FROM users"))
        if res.scalar() > 0:
            print("Database already seeded. Skipping.")
            return

        print("Seeding database with mock data...")

        # Create main user
        main_user = User(
            id=uuid.uuid4(),
            hemis_id="admin_hemis",
            full_name="Akbarali",
            university="Muhammad al-Xorazmiy nomidagi TATU",
            faculty="Dasturiy injiniring",
            course=3,
            coin_balance=1500,
        )
        session.add(main_user)

        # Create other users
        universities = ["TATU", "O'zMU", "TDYU", "TDTU", "INHA"]
        first_names = ["Jasur", "Murod", "Sardor", "Iroda", "Aziza", "Malika", "Javohir", "Bekzod", "Nodira", "Zilola"]
        last_names = ["Toshmatov", "Aliev", "Valiev", "Qodirov", "Sodiqova", "Umarova", "Nazarov", "Karimov"]

        other_users = []
        for i in range(50):
            user = User(
                id=uuid.uuid4(),
                hemis_id=f"hemis_{i}",
                full_name=f"{random.choice(first_names)} {random.choice(last_names)}",
                university=random.choice(universities),
                faculty="Axborot xavfsizligi",
                course=random.randint(1,4),
                coin_balance=random.randint(100, 1000),
            )
            other_users.append(user)
            session.add(user)
        
        await session.commit()
        print(f"Created 50 users.")

        # Create skills
        subjects = ["Matematika", "Fizika", "Dasturlash", "Kriptografiya", "Ingliz tili", "Tarix", "Ma'lumotlar bazasi"]
        
        for user in other_users:
            # can teach
            for _ in range(random.randint(0, 2)):
                session.add(Skill(user_id=user.id, skill_name=random.choice(subjects), type=SkillType.can_teach, level=random.randint(1, 5)))
            # want learn
            for _ in range(random.randint(1, 3)):
                session.add(Skill(user_id=user.id, skill_name=random.choice(subjects), type=SkillType.want_learn))

        await session.commit()
        print(f"Created skills.")

        # Create P2P Requests
        requests = []
        for i in range(30):
            requester = random.choice(other_users)
            req = P2PRequest(
                id=uuid.uuid4(),
                requester_id=requester.id,
                subject=random.choice(subjects),
                description=f"Bu masala bo'yicha yordam kerak: {random.choice(subjects)}. Kim tushuntirib bera oladi?",
                coin_offer=random.randint(10, 50),
                status="open"
            )
            requests.append(req)
            session.add(req)
        
        await session.commit()
        print(f"Created 30 P2P requests.")

        # Create a few matches
        for req in requests[:10]:
            req.status = "matched"
            helper = random.choice([u for u in other_users if u.id != req.requester_id])
            match = P2PMatch(
                id=uuid.uuid4(),
                request_id=req.id,
                helper_id=helper.id,
                status="active"
            )
            session.add(match)
        
        await session.commit()
        print("Created matches.")
        print("Seeding completed successfully!")

if __name__ == "__main__":
    asyncio.run(seed_db())
