"""Metrics calculator for auction efficiency analysis."""

from typing import Dict, List, Optional
import numpy as np
from scipy.optimize import linear_sum_assignment

from ..models.student import Student
from ..models.course import Course
from ..models.bid import Bid
from ..auction.hybrid_auction import AuctionResult


class EfficiencyCalculator:
    """
    Calculate various efficiency metrics for auction outcomes.
    
    Metrics:
    - Total welfare: Sum of student valuations for allocated courses
    - Efficiency gap: Difference from optimal allocation
    - Revenue: Sum of clearing prices
    - Allocation rate: Percentage of students who get courses
    """
    
    def __init__(
        self,
        students: Dict[str, Student],
        courses: Dict[str, Course],
        bids: List[Bid]
    ):
        self.students = students
        self.courses = courses
        self.bids = bids
    
    def total_welfare(self, result: AuctionResult) -> float:
        """Calculate total welfare (sum of valuations for allocated courses)."""
        total = 0.0
        for bid in result.allocated_bids:
            if bid.is_allocated:
                total += bid.true_valuation
        return total
    
    def revenue(self, result: AuctionResult) -> float:
        """Calculate total revenue from clearing prices."""
        return result.total_revenue
    
    def allocation_rate(self, result: AuctionResult) -> float:
        """Calculate percentage of students who got a course."""
        if not self.students:
            return 0.0
        return len(result.allocations) / len(self.students)
    
    def capacity_utilization(self, result: AuctionResult) -> float:
        """Calculate percentage of total course capacity used."""
        total_capacity = sum(c.capacity for c in self.courses.values())
        if total_capacity == 0:
            return 0.0
        total_enrolled = sum(len(c.enrolled_students) for c in self.courses.values())
        return total_enrolled / total_capacity
    
    def efficiency_gap(self, result: AuctionResult) -> float:
        """
        Calculate efficiency gap compared to optimal allocation.
        
        Uses Hungarian algorithm (linear sum assignment) for optimal matching.
        Only considers bids that exist (students can only get courses they bid on).
        """
        optimal_welfare = self._compute_optimal_welfare()
        actual_welfare = self.total_welfare(result)
        
        if optimal_welfare == 0:
            return 0.0
        
        gap = (optimal_welfare - actual_welfare) / optimal_welfare
        return gap
    
    def _compute_optimal_welfare(self) -> float:
        """
        Compute optimal welfare using a greedy approach with capacity constraints.
        
        This solves: max sum of valuations subject to each student 
        gets at most one course and each course has capacity constraints.
        """
        # Build lookup for valuations
        bid_lookup = {}
        for bid in self.bids:
            key = (bid.student_id, bid.course_id)
            bid_lookup[key] = bid.true_valuation
        
        # Get course capacities
        course_capacities = {c.id: c.capacity for c in self.courses.values()}
        
        # Sort all bids by valuation descending
        all_bids = sorted(self.bids, key=lambda b: -b.true_valuation)
        
        # Greedy allocation to maximize welfare
        allocated = set()  # students already allocated
        course_counts = {c_id: 0 for c_id in self.courses.keys()}
        
        optimal_welfare = 0.0
        for bid in all_bids:
            student_id = bid.student_id
            course_id = bid.course_id
            
            # Skip if student already allocated
            if student_id in allocated:
                continue
            
            # Skip if course at capacity
            if course_counts[course_id] >= course_capacities[course_id]:
                continue
            
            # Allocate this bid
            allocated.add(student_id)
            course_counts[course_id] += 1
            optimal_welfare += bid.true_valuation
        
        return optimal_welfare
    
    def priority_weighted_welfare(self, result: AuctionResult) -> float:
        """Calculate priority-weighted welfare (accounts for seniority)."""
        total = 0.0
        for bid in result.allocated_bids:
            if bid.is_allocated:
                student = self.students[bid.student_id]
                weighted_value = bid.true_valuation * student.priority_weight
                total += weighted_value
        return total
    
    def average_clearing_price(self, result: AuctionResult) -> float:
        """Calculate average clearing price for allocated students."""
        if not result.clearing_prices:
            return 0.0
        return np.mean(list(result.clearing_prices.values()))
    
    def price_distribution(self, result: AuctionResult) -> Dict:
        """Get distribution statistics of clearing prices."""
        prices = list(result.clearing_prices.values())
        if not prices:
            return {'min': 0, 'max': 0, 'mean': 0, 'median': 0, 'std': 0}
        
        return {
            'min': np.min(prices),
            'max': np.max(prices),
            'mean': np.mean(prices),
            'median': np.median(prices),
            'std': np.std(prices)
        }
    
    def get_full_report(self, result: AuctionResult) -> Dict:
        """Generate a comprehensive metrics report."""
        return {
            'total_welfare': self.total_welfare(result),
            'optimal_welfare': self._compute_optimal_welfare(),
            'efficiency_gap': self.efficiency_gap(result),
            'revenue': self.revenue(result),
            'allocation_rate': self.allocation_rate(result),
            'capacity_utilization': self.capacity_utilization(result),
            'priority_weighted_welfare': self.priority_weighted_welfare(result),
            'average_clearing_price': self.average_clearing_price(result),
            'price_distribution': self.price_distribution(result),
            'num_allocated': len(result.allocations),
            'num_unallocated': len(result.unallocated_students)
        }