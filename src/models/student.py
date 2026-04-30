"""Student model for course auction simulation."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Student:
    """Represents a student in the course auction."""
    
    id: str
    seniority_years: int  # 1-4 years
    virtual_budget: float = 1000.0
    allocated_course: Optional[str] = None
    clearing_price: float = 0.0
    
    def __post_init__(self):
        # Priority weight: linear formula with mild seniority bonus (1.0 + 0.1 * seniority)
        # This gives: Year 1=1.1, Year 2=1.2, Year 3=1.3, Year 4=1.4
        # Max priority ratio: 1.4/1.1 ≈ 27% (vs previous 60%)
        self.priority_weight = 1.0 + 0.1 * self.seniority_years
    
    def effective_bid(self, bid_amount: float) -> float:
        """Calculate effective bid with priority weight."""
        return bid_amount * self.priority_weight
    
    def __repr__(self) -> str:
        return f"Student(id={self.id}, seniority={self.seniority_years}y, budget={self.virtual_budget})"