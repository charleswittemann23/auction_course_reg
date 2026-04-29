"""Course model for course auction simulation."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class Course:
    """Represents a course in the auction."""
    
    id: str
    name: str
    capacity: int
    reserve_price: float = 0.0  # Minimum price to accept
    enrolled_students: List[str] = field(default_factory=list)
    
    def is_full(self) -> bool:
        """Check if course is at capacity."""
        return len(self.enrolled_students) >= self.capacity
    
    def enroll(self, student_id: str) -> bool:
        """Enroll a student if capacity allows."""
        if self.is_full():
            return False
        if student_id not in self.enrolled_students:
            self.enrolled_students.append(student_id)
        return True
    
    def __repr__(self) -> str:
        return f"Course(id={self.id}, name={self.name}, capacity={self.capacity}, enrolled={len(self.enrolled_students)})"