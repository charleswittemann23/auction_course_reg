"""Random Serial Dictatorship (RSD) mechanism for course allocation.

This simulates the current system where:
1. Students are randomly assigned enrollment times (priority order)
2. Each student, in order of their enrollment time, picks their most preferred available course
3. Continues until all students have chosen or all courses are full

This serves as a baseline comparison to the auction mechanism.
"""

import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from ..models.student import Student
from ..models.course import Course
from ..models.bid import Bid


@dataclass
class RSDResult:
    """Result of an RSD run."""
    
    allocations: Dict[str, str]  # student_id -> course_id
    total_welfare: float
    allocated_bids: List[Bid]
    unallocated_students: List[str]
    enrollment_order: List[str]  # The random order students were called


class RandomSerialDictatorship:
    """
    Random Serial Dictatorship mechanism.
    
    In this mechanism:
    1. A random ordering of students is generated (enrollment times)
    2. Each student, in turn, is allocated to their highest-valued available course
    3. Students who don't get any of their choices remain unallocated
    
    This is strategy-proof: students have no incentive to misreport preferences.
    """
    
    def __init__(self, random_seed: Optional[int] = None):
        if random_seed is not None:
            random.seed(random_seed)
        self.students: Dict[str, Student] = {}
        self.courses: Dict[str, Course] = {}
        self.bids: List[Bid] = []
    
    # =========================================================================
    # Data Generation Methods (reuse from HybridAuction)
    # =========================================================================
    
    def generate_students(self, n: int, min_budget: float = 500, max_budget: float = 2000) -> Dict[str, Student]:
        """Generate n students with random seniority and budgets."""
        self.students = {}
        for i in range(n):
            student_id = f"S{i+1:03d}"
            seniority = random.randint(1, 4)
            budget = random.uniform(min_budget, max_budget)
            self.students[student_id] = Student(
                id=student_id,
                seniority_years=seniority,
                virtual_budget=budget
            )
        return self.students
    
    def generate_courses(self, course_specs: List[Dict]) -> Dict[str, Course]:
        """Generate courses from specifications."""
        self.courses = {}
        for spec in course_specs:
            self.courses[spec['id']] = Course(
                id=spec['id'],
                name=spec['name'],
                capacity=spec['capacity'],
                reserve_price=spec.get('reserve_price', 0.0)
            )
        return self.courses
    
    def generate_bids(
        self,
        bids_per_student: Tuple[int, int] = (2, 5),
        min_bid: float = 50,
        max_bid_fraction: float = 0.8
    ) -> List[Bid]:
        """
        Generate random bids for students.
        
        Each student bids on a random subset of courses.
        Bid amount is random fraction of their budget.
        True valuation is correlated with bid (with noise).
        """
        self.bids = []
        
        for student in self.students.values():
            # Random number of courses to bid on
            num_bids = random.randint(bids_per_student[0], bids_per_student[1])
            
            # Random subset of courses
            available_courses = list(self.courses.keys())
            if len(available_courses) <= num_bids:
                course_subset = available_courses
            else:
                course_subset = random.sample(available_courses, num_bids)
            
            for course_id in course_subset:
                course = self.courses[course_id]
                
                # Bid amount: random fraction of student's budget
                max_allowed = student.virtual_budget * max_bid_fraction
                bid_amount = random.uniform(min_bid, max_allowed)
                
                # True valuation: correlated with bid but with noise
                noise = random.uniform(-0.2, 0.3)
                true_valuation = bid_amount * (1 + noise)
                true_valuation = max(10, true_valuation)
                
                self.bids.append(Bid(
                    student_id=student.id,
                    course_id=course_id,
                    bid_amount=bid_amount,
                    true_valuation=true_valuation
                ))
        
        return self.bids
    
    # =========================================================================
    # Allocation Methods
    # =========================================================================
    
    def allocate(self, use_seniority_priority: bool = True) -> RSDResult:
        """
        Run the Random Serial Dictatorship allocation.
        
        Args:
            use_seniority_priority: If True, seniors (higher seniority) get called 
                before juniors. Within each seniority cohort, order is random.
                If False, all students are randomly ordered (pure random serial dictatorship).
        
        Steps:
            1. Generate enrollment order (random within seniority cohorts, or fully random)
            2. For each student in order, allocate to highest-valued available course
            3. Track allocations and compute welfare
        """
        # Step 1: Generate enrollment order
        if use_seniority_priority:
            # Seniority-based priority: seniors go first, then juniors, etc.
            # Within each seniority level, order is random
            student_ids = self._generate_seniority_order()
        else:
            # Pure random serial dictatorship: fully random order
            student_ids = list(self.students.keys())
            random.shuffle(student_ids)
        
        # Step 2: Build preference lookup (student -> sorted list of course preferences)
        # Preferences are based on true valuation
        student_preferences = self._build_preferences()
        
        # Step 3: Allocate students in serial order
        allocations = {}  # student_id -> course_id
        allocated_bids = []
        
        for student_id in student_ids:
            # Get this student's course preferences (sorted by valuation descending)
            preferences = student_preferences.get(student_id, [])
            
            # Try to allocate to their most preferred available course
            for course_id in preferences:
                course = self.courses[course_id]
                
                if not course.is_full():
                    # Allocate student to this course
                    allocations[student_id] = course_id
                    course.enroll(student_id)
                    
                    # Find and mark the corresponding bid
                    for bid in self.bids:
                        if bid.student_id == student_id and bid.course_id == course_id:
                            bid.is_allocated = True
                            allocated_bids.append(bid)
                            break
                    
                    break  # Student is allocated, move to next student
        
        # Step 4: Calculate total welfare
        total_welfare = sum(bid.true_valuation for bid in allocated_bids)
        
        # Find unallocated students
        allocated_students = set(allocations.keys())
        unallocated_students = [
            sid for sid in self.students.keys() if sid not in allocated_students
        ]
        
        return RSDResult(
            allocations=allocations,
            total_welfare=total_welfare,
            allocated_bids=allocated_bids,
            unallocated_students=unallocated_students,
            enrollment_order=student_ids
        )
    
    def _build_preferences(self) -> Dict[str, List[str]]:
        """
        Build preference rankings for each student based on true valuations.
        
        Returns:
            Dict mapping student_id to list of course_ids sorted by valuation descending
        """
        preferences = {}
        
        for student in self.students.values():
            # Get all bids by this student
            student_bids = [b for b in self.bids if b.student_id == student.id]
            
            # Sort by true valuation descending
            student_bids.sort(key=lambda b: -b.true_valuation)
            
            # Extract course preferences
            preferences[student.id] = [bid.course_id for bid in student_bids]
        
        return preferences
    
    def _generate_seniority_order(self) -> List[str]:
        """
        Generate enrollment order with seniority priority.
        
        Seniors (4th years) go first, then juniors (3rd), sophomores (2nd),
        and finally freshmen (1st). Within each seniority cohort, order is random.
        
        This simulates a system where:
        - 4th years get randomly assigned early times
        - 3rd years get randomly assigned after all 4th years
        - 2nd years get randomly assigned after all 3rd years
        - 1st years get randomly assigned after all 2nd years
        """
        # Group students by seniority (descending - seniors first)
        seniority_groups = {}
        for student in self.students.values():
            seniority = student.seniority_years
            if seniority not in seniority_groups:
                seniority_groups[seniority] = []
            seniority_groups[seniority].append(student.id)
        
        # Shuffle within each seniority group
        for seniority in seniority_groups:
            random.shuffle(seniority_groups[seniority])
        
        # Build final order: 4th years first, then 3rd, 2nd, 1st
        final_order = []
        for seniority in sorted(seniority_groups.keys(), reverse=True):
            final_order.extend(seniority_groups[seniority])
        
        return final_order
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def get_summary(self) -> Dict:
        """Get a summary of the RSD state."""
        return {
            'num_students': len(self.students),
            'num_courses': len(self.courses),
            'num_bids': len(self.bids),
            'total_capacity': sum(c.capacity for c in self.courses.values())
        }
    
    def print_result(self, result: RSDResult):
        """Print a formatted result."""
        print("\n" + "="*60)
        print("RANDOM SERIAL DICTATORSHIP RESULT")
        print("="*60)
        print(f"\nAllocations: {len(result.allocations)} students")
        print(f"Unallocated: {len(result.unallocated_students)} students")
        print(f"Total Welfare: ${result.total_welfare:,.2f}")
        
        print(f"\nEnrollment Order (first 10):")
        for i, sid in enumerate(result.enrollment_order[:10]):
            course = result.allocations.get(sid, "None")
            print(f"  {i+1}. {sid} -> {course}")