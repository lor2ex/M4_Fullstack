from fastapi import APIRouter, HTTPException
from typing import List
from app.db.models.person import PersonCreate, PersonRead
from app.db.repository import PersonRepository

router = APIRouter(prefix="/people", tags=["people"])

@router.get("/", response_model=List[PersonRead])
async def read_people():
    return await PersonRepository.list_people()

@router.post("/", response_model=PersonRead)
async def add_person(person: PersonCreate):
    return await PersonRepository.create_person(person.name, person.age, person.email)

@router.put("/{person_id}/email")
async def update_email(person_id: int, new_email: str):
    updated = await PersonRepository.update_email(person_id, new_email)
    if not updated:
        raise HTTPException(status_code=404, detail="Person not found")
    return {"message": "Email updated successfully"}

@router.delete("/{person_id}")
async def delete_person(person_id: int):
    deleted = await PersonRepository.delete_person(person_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Person not found")
    return {"message": "Person deleted successfully"}
