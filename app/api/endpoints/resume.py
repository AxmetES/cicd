from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.models import Education, Experience, Project, Resume, User
from app.schemas.resume_schemas import (
    EducationCreate,
    EducationResponse,
    ExperienceCreate,
    ExperienceResponse,
    ProjectCreate,
    ProjectResponse,
    ResumeResponse,
    ResumeUpdate,
)
from app.storage import upload_photo

router = APIRouter(prefix="/api/resume", tags=["resume"])


def _resume_with_relations_query():
    return select(Resume).options(
        selectinload(Resume.experience),
        selectinload(Resume.education),
        selectinload(Resume.projects),
    )


async def _get_own_resume(current_user: User, db: AsyncSession, *, with_relations: bool = False) -> Resume | None:
    query = _resume_with_relations_query() if with_relations else select(Resume)
    result = await db.execute(query.where(Resume.user_id == current_user.id))
    return result.scalar_one_or_none()


@router.get("/me", response_model=ResumeResponse)
async def get_my_resume(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resume = await _get_own_resume(current_user, db, with_relations=True)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume


@router.post("/me/photo")
async def upload_resume_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Resume).where(Resume.user_id == current_user.id))
    resume = result.scalar_one_or_none()

    if not resume:
        resume = Resume(
            user_id=current_user.id,
            slug=f"user-{current_user.id}",
            full_name="",
            role="",
            description="",
        )
        db.add(resume)
        await db.flush()

    photo_url = upload_photo(file.file, file.content_type)

    resume.photo_url = photo_url
    await db.commit()

    return {"photo_url": photo_url}


@router.put("/me", response_model=ResumeResponse)
async def upsert_my_resume(
    data: ResumeUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Resume).where(Resume.slug == data.slug))
    slug_owner = result.scalar_one_or_none()

    resume = await _get_own_resume(current_user, db)

    if slug_owner and (not resume or slug_owner.id != resume.id):
        raise HTTPException(status_code=400, detail="Slug already taken")

    if resume:
        resume.slug = data.slug
        resume.full_name = data.full_name
        resume.role = data.role
        resume.description = data.description
        resume.location = data.location
    else:
        resume = Resume(
            user_id=current_user.id,
            slug=data.slug,
            full_name=data.full_name,
            role=data.role,
            description=data.description,
            location=data.location
        )
        db.add(resume)

    await db.commit()

    return await _get_own_resume(current_user, db, with_relations=True)


@router.get("/public/{slug}", response_model=ResumeResponse)
async def get_public_resume(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(_resume_with_relations_query().where(Resume.slug == slug))
    resume = result.scalar_one_or_none()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    return resume


@router.post("/me/experience", response_model=ExperienceResponse)
async def add_experience(
    data: ExperienceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resume = await _get_own_resume(current_user, db)

    if not resume:
        raise HTTPException(status_code=404, detail="Резюме не найдено, создайте резюме сначала")

    experience = Experience(resume_id=resume.id, **data.model_dump())
    db.add(experience)
    await db.commit()
    await db.refresh(experience)

    return experience


@router.put("/me/experience/{experience_id}", response_model=ExperienceResponse)
async def update_experience(
    experience_id: int,
    data: ExperienceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Experience)
        .join(Resume, Experience.resume_id == Resume.id)
        .where(Experience.id == experience_id, Resume.user_id == current_user.id)
    )
    experience = result.scalar_one_or_none()

    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found")

    experience.role = data.role
    experience.company = data.company
    experience.period = data.period
    experience.description = data.description

    await db.commit()
    await db.refresh(experience)

    return experience


@router.delete("/me/experience/{experience_id}")
async def delete_experience(
    experience_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Experience)
        .join(Resume, Experience.resume_id == Resume.id)
        .where(Experience.id == experience_id, Resume.user_id == current_user.id)
    )
    experience = result.scalar_one_or_none()

    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found")

    await db.delete(experience)
    await db.commit()

    return {"message": "Experience deleted"}


@router.post("/me/education", response_model=EducationResponse)
async def add_education(
    data: EducationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resume = await _get_own_resume(current_user, db)

    if not resume:
        raise HTTPException(status_code=404, detail="Резюме не найдено, создайте резюме сначала")

    education = Education(resume_id=resume.id, **data.model_dump())
    db.add(education)
    await db.commit()
    await db.refresh(education)

    return education


@router.put("/me/education/{education_id}", response_model=EducationResponse)
async def update_education(
    education_id: int,
    data: EducationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Education)
        .join(Resume, Education.resume_id == Resume.id)
        .where(Education.id == education_id, Resume.user_id == current_user.id)
    )
    education = result.scalar_one_or_none()

    if not education:
        raise HTTPException(status_code=404, detail="Education not found")

    education.title = data.title
    education.place = data.place
    education.period = data.period
    education.description = data.description

    await db.commit()
    await db.refresh(education)

    return education


@router.delete("/me/education/{education_id}")
async def delete_education(
    education_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Education)
        .join(Resume, Education.resume_id == Resume.id)
        .where(Education.id == education_id, Resume.user_id == current_user.id)
    )
    education = result.scalar_one_or_none()

    if not education:
        raise HTTPException(status_code=404, detail="Education not found")

    await db.delete(education)
    await db.commit()

    return {"message": "Education deleted"}


@router.post("/me/projects", response_model=ProjectResponse)
async def add_project(
    data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resume = await _get_own_resume(current_user, db)

    if not resume:
        raise HTTPException(status_code=404, detail="Резюме не найдено, создайте резюме сначала")

    project = Project(resume_id=resume.id, **data.model_dump())
    db.add(project)
    await db.commit()
    await db.refresh(project)

    return project


@router.put("/me/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project)
        .join(Resume, Project.resume_id == Resume.id)
        .where(Project.id == project_id, Resume.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.name = data.name
    project.url = data.url
    project.description = data.description

    await db.commit()
    await db.refresh(project)

    return project


@router.delete("/me/projects/{project_id}")
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project)
        .join(Resume, Project.resume_id == Resume.id)
        .where(Project.id == project_id, Resume.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.delete(project)
    await db.commit()

    return {"message": "Project deleted"}
