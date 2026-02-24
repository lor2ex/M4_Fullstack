from sqlalchemy import select, func
from app.db import AsyncSessionLocal
from app.db.models.person import Person

class PersonRepository:

    @staticmethod
    async def is_table_empty() -> bool:
        async with AsyncSessionLocal() as session:
            count = await session.scalar(select(func.count()).select_from(Person))
            return count == 0

    @staticmethod
    async def list_people() -> list[Person]:
        async with AsyncSessionLocal() as session:
            result = await session.scalars(select(Person))
            return result.all()

    @staticmethod
    async def create_person(name: str, age: int | None, email: str) -> Person:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                person = Person(name=name, age=age, email=email)
                session.add(person)
            return person

    @staticmethod
    async def update_email(person_id: int, new_email: str) -> bool:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                person = await session.get(Person, person_id)
                if not person:
                    return False
                person.email = new_email
                return True

    @staticmethod
    async def delete_person(person_id: int) -> bool:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                person = await session.get(Person, person_id)
                if not person:
                    return False
                await session.delete(person)
                return True
