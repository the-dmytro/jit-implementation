from typing import List

from pydantic import BaseModel, Field


class SubmitVersion(BaseModel):
    imports: List[str] = Field(..., description="Required imports")
    code: str = Field(..., description="Code of the object (without import statements)")


class Reasoning(BaseModel):
    chain_of_thought: List[str] = Field(..., description="Chain of thought")


class ReadSourceCode(BaseModel):
    type: str = Field(
        ...,
        description="Name of the project type whose source code should be read",
    )


class GenerationOutput(BaseModel):
    imports: list[str] = Field(..., description="Required imports")
    code: str = Field(..., description="Implementation code without import statements")
    chain_of_thought: list[str] = Field(
        default_factory=list,
        description="Brief reasoning steps",
    )


class BatchGenerationOutput(BaseModel):
    implementations: dict[str, GenerationOutput] = Field(
        ...,
        description="Map of stub name to implementation payload",
    )
