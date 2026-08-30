from pydantic import BaseModel, ConfigDict


class ResumeUpdate(BaseModel):
    slug: str
    full_name: str
    role: str
    description: str
    location: str | None = None


class ExperienceCreate(BaseModel):
    role: str
    company: str
    period: str
    description: str


class EducationCreate(BaseModel):
    title: str
    place: str
    period: str
    description: str


class ProjectCreate(BaseModel):
    name: str
    url: str
    description: str


class ExperienceResponse(ExperienceCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class EducationResponse(EducationCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class ProjectResponse(ProjectCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class ResumeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    slug: str
    full_name: str
    role: str
    description: str
    location: str | None = None
    photo_url: str | None = None
    experience: list[ExperienceResponse] = []
    education: list[EducationResponse] = []
    projects: list[ProjectResponse] = []
