"""Hybrid Auction mechanism for course allocation with clearing prices."""

import random
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

from ..models.student import Student
from ..models.course import Course
from ..models.bid import Bid


@dataclass
class AuctionResult:
    """Result of an auction run."""
    
    allocations: Dict[str, str]  # student_id -> course_id
    clearing_prices: Dict[str, float]  # student_id -> price paid
    total_revenue: float
    allocated_bids: List[Bid]
    unallocated_students: List[str]


class HybridAuction:
    """
    Hybrid auction mechanism combining priority (seniority) with monetary bids.
    
    Mechanism:
    1. Students submit bids for courses
    2. Effective bid = bid_amount * priority_weight (based on seniority)
    3. Allocate greedily by effective bid until capacity reached
    4. Compute clearing prices using VCG-style externality pricing
    """
    
    def __init__(self, random_seed: Optional[int] = None):
        if random_seed is not None:
            random.seed(random_seed)
        self.students: Dict[str, Student] = {}
        self.courses: Dict[str, Course] = {}
        self.bids: List[Bid] = []
    
    # =========================================================================
    # Data Generation Methods
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
        """
        Generate courses from specifications.
        
        Args:
            course_specs: List of dicts with 'id', 'name', 'capacity', 'reserve_price'
        """
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
                # Strategic bidders might bid below true value
                noise = random.uniform(-0.2, 0.3)  # -20% to +30% noise
                true_valuation = bid_amount * (1 + noise)
                true_valuation = max(10, true_valuation)  # Minimum value
                
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
    
    def allocate(self) -> AuctionResult:
        """
        Run the hybrid auction allocation.
        
        Steps:
        1. Sort all bids by priority-weighted valuation (true_valuation * priority_weight) descending
        2. Greedily allocate bids to courses if capacity allows
        3. Compute clearing prices for allocated students
        """
        # Step 1: Calculate priority-weighted valuations and sort
        scored_bids = []
        for bid in self.bids:
            student = self.students[bid.student_id]
            # Priority-weighted valuation (not bid!)
            priority_weighted_val = bid.true_valuation * student.priority_weight
            scored_bids.append((priority_weighted_val, bid))
        
        # Sort by priority-weighted valuation descending
        scored_bids.sort(key=lambda x: -x[0])
        
        # Step 2: Greedy allocation
        allocations = {}  # student_id -> course_id
        allocated_bids = []
        
        for _, bid in scored_bids:
            student_id = bid.student_id
            course_id = bid.course_id
            
            # Skip if student already allocated
            if student_id in allocations:
                continue
            
            # Skip if course is full
            course = self.courses[course_id]
            if course.is_full():
                continue
            
            # Skip if bid is below reserve price
            if bid.bid_amount < course.reserve_price:
                continue
            
            # Allocate student to course
            allocations[student_id] = course_id
            course.enroll(student_id)
            bid.is_allocated = True
            allocated_bids.append(bid)
        
        # Step 3: Compute clearing prices
        clearing_prices = self._compute_clearing_prices(allocated_bids, allocations)
        
        # Calculate total revenue
        total_revenue = sum(clearing_prices.values())
        
        # Find unallocated students
        allocated_students = set(allocations.keys())
        unallocated_students = [
            sid for sid in self.students.keys() if sid not in allocated_students
        ]
        
        return AuctionResult(
            allocations=allocations,
            clearing_prices=clearing_prices,
            total_revenue=total_revenue,
            allocated_bids=allocated_bids,
            unallocated_students=unallocated_students
        )
    
    def _compute_clearing_prices(
        self,
        allocated_bids: List[Bid],
        allocations: Dict[str, str]
    ) -> Dict[str, float]:
        """
        Compute clearing prices: each allocated student pays based on priority-weighted valuation.
        """
        clearing_prices = {}
        # Build a lookup for all bids by course
        course_bids = {}
        for bid in self.bids:
            course_bids.setdefault(bid.course_id, []).append(bid)

        for bid in allocated_bids:
            student_id = bid.student_id
            course_id = bid.course_id
            student = self.students[student_id]
            course = self.courses[course_id]

            # Get all bids for this course, sorted by priority-weighted valuation descending
            bids_for_course = course_bids[course_id]
            bids_for_course_sorted = sorted(
                bids_for_course,
                key=lambda b: -b.true_valuation * self.students[b.student_id].priority_weight
            )

            # Find the cutoff: the first unallocated bid after the allocated ones
            allocated_ids = set(b.student_id for b in allocated_bids if b.course_id == course_id)
            allocated_count = len(allocated_ids)
            clearing_price = course.reserve_price
            found = False
            count = 0
            for b in bids_for_course_sorted:
                if b.student_id in allocated_ids:
                    count += 1
                else:
                    if count == course.capacity:
                        # This is the first unallocated bid after all seats filled
                        # Use priority-weighted valuation as price
                        pw_val = b.true_valuation * self.students[b.student_id].priority_weight
                        clearing_price = max(pw_val / self.students[b.student_id].priority_weight, course.reserve_price)
                        found = True
                        break
            # If not enough unallocated bids, use reserve price
            clearing_price = min(clearing_price, student.virtual_budget)
            clearing_prices[student_id] = clearing_price

        return clearing_prices
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def get_summary(self) -> Dict:
        """Get a summary of the auction state."""
        return {
            'num_students': len(self.students),
            'num_courses': len(self.courses),
            'num_bids': len(self.bids),
            'total_capacity': sum(c.capacity for c in self.courses.values()),
        }
    
    def reset(self):
        """Reset the auction state."""
        self.students = {}
        self.courses = {}
        self.bids = []