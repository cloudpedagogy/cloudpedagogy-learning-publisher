from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from enum import Enum


class RenderMode(str, Enum):
    SINGLE_PAGE = "single_page"
    MULTI_PAGE = "multi_page"


class NavigationStyle(str, Enum):
    DEFAULT = "default"
    NUMBERED_SUBPAGES = "numbered_subpages"


class Resource(BaseModel):
    title: str
    file: str
    output_file: str
    display: str


class Page(BaseModel):
    id: Optional[str] = None
    title: str
    kind: str
    description: Optional[str] = None
    source_docx: Optional[str] = None
    resources: List[Resource] = Field(default_factory=list)
    interactions: List[Dict] = Field(default_factory=list)


class Section(BaseModel):
    id: Optional[str] = None
    number: int
    title: str
    kind: str
    navigation_style: NavigationStyle = NavigationStyle.DEFAULT
    subpage_count: Optional[int] = None
    interactions: List[Dict] = Field(default_factory=list)
    pages: List[Page] = Field(default_factory=list)
    subpages: List[Page] = Field(default_factory=list)

    @property
    def effective_pages(self) -> List[Page]:
        """Returns subpages if available, otherwise fallback to pages."""
        return self.subpages if self.subpages else self.pages

    def validate_structure(self):
        """Custom validation for subpage count."""
        if self.subpages:
            if self.subpage_count is not None and self.subpage_count != len(self.subpages):
                raise ValueError(
                    f"Section {self.number}: subpage_count ({self.subpage_count}) "
                    f"does not match actual subpages length ({len(self.subpages)})"
                )


class SessionOptions(BaseModel):
    include_prerequisites: bool = False
    include_maths: bool = False
    include_quiz: bool = False
    include_r_code: bool = False


class Session(BaseModel):
    id: Optional[str] = None
    code: str
    title: str
    type: str = "standard"
    required: bool = True
    render_mode: Optional[RenderMode] = None
    overview: str
    learning_objectives: List[str] = Field(default_factory=list)
    sections: List[Section] = Field(default_factory=list)
    interactions: List[Dict] = Field(default_factory=list)
    options: Optional[SessionOptions] = None


class Module(BaseModel):
    id: Optional[str] = None
    code: str
    title: str
    description: str
    default_render_mode: RenderMode = RenderMode.SINGLE_PAGE
    default_subpage_count: int = 7
    interactions: List[Dict] = Field(default_factory=list)
    metadata: Optional[Dict] = None


class CourseConfig(BaseModel):
    module: Module
    sessions: List[Session]
    # Optional course-level pages appear in the sidebar alongside sessions.
    # Examples include a glossary, references, accessibility statement, or help page.
    standalone_pages: List[Page] = Field(default_factory=list)
