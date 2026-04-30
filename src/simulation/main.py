"""Simulation runner for hybrid auction experiments."""

import argparse
import json
import random
from typing import Dict, List, Optional
from dataclasses import asdict
import numpy as np

from ..auction.hybrid_auction import HybridAuction
from ..auction.rsd_mechanism import RandomSerialDictatorship
from ..analysis.metrics import EfficiencyCalculator
from ..models.course import Course
from ..models.bid import Bid


def create_default_courses(num_courses: int = 5) -> List[Dict]:
    """Create default course specifications."""
    course_names = [
        "Intro to Economics",
        "Calculus I",
        "Computer Science Fundamentals",
        "Statistics",
        "Financial Accounting",
        "Marketing Principles",
        "Operations Management",
        "Data Structures",
        "Microeconomics",
        "Macroeconomics"
    ]
    
    courses = []
    for i in range(num_courses):
        courses.append({
            'id': f"C{i+1:02d}",
            'name': course_names[i % len(course_names)],
            'capacity': random.randint(15, 40),
            'reserve_price': random.uniform(20, 100)
        })
    return courses


def run_single_auction(
    n_students: int,
    n_courses: int,
    random_seed: Optional[int] = None,
    bids_per_student: tuple = (2, 5)
) -> Dict:
    """Run a single auction and return results."""
    auction = HybridAuction(random_seed=random_seed)
    
    # Generate data
    auction.generate_students(n_students)
    courses = create_default_courses(n_courses)
    auction.generate_courses(courses)
    auction.generate_bids(bids_per_student=bids_per_student)
    
    # Run auction
    result = auction.allocate()
    
    # Calculate metrics
    calculator = EfficiencyCalculator(
        auction.students,
        auction.courses,
        auction.bids
    )
    metrics = calculator.get_full_report(result)
    
    return {
        'parameters': {
            'n_students': n_students,
            'n_courses': n_courses,
            'random_seed': random_seed
        },
        'allocations': result.allocations,
        'clearing_prices': result.clearing_prices,
        'metrics': metrics
    }


def run_batch_simulation(
    n_students: int,
    n_courses: int,
    n_runs: int = 10,
    bids_per_student: tuple = (2, 5)
) -> Dict:
    """Run multiple auctions and aggregate results."""
    results = []
    
    for i in range(n_runs):
        seed = random.randint(1, 100000)
        result = run_single_auction(
            n_students=n_students,
            n_courses=n_courses,
            random_seed=seed,
            bids_per_student=bids_per_student
        )
        results.append(result)
    
    # Aggregate metrics
    metric_keys = [
        'total_welfare', 'optimal_welfare', 'efficiency_gap', 'revenue',
        'allocation_rate', 'capacity_utilization', 'average_clearing_price'
    ]
    
    aggregated = {}
    for key in metric_keys:
        values = [r['metrics'][key] for r in results]
        aggregated[key] = {
            'mean': np.mean(values),
            'std': np.std(values),
            'min': np.min(values),
            'max': np.max(values)
        }
    
    return {
        'parameters': {
            'n_students': n_students,
            'n_courses': n_courses,
            'n_runs': n_runs
        },
        'aggregated_metrics': aggregated,
        'individual_results': results
    }


def print_report(report: Dict, verbose: bool = False):
    """Print a formatted report."""
    params = report['parameters']
    print("\n" + "="*60)
    print("HYBRID AUCTION SIMULATION REPORT")
    print("="*60)
    print(f"\nParameters:")
    print(f"  Students: {params['n_students']}")
    print(f"  Courses: {params['n_courses']}")
    if 'n_runs' in params:
        print(f"  Runs: {params['n_runs']}")
    
    if 'aggregated_metrics' in report:
        # Batch results
        metrics = report['aggregated_metrics']
        print(f"\n{'Metric':<30} {'Mean':>10} {'Std':>10} {'Min':>10} {'Max':>10}")
        print("-"*70)
        
        for key, values in metrics.items():
            print(f"  {key:<28} {values['mean']:>10.2f} {values['std']:>10.2f} {values['min']:>10.2f} {values['max']:>10.2f}")
    else:
        # Single run results
        metrics = report['metrics']
        print(f"\nEfficiency Metrics:")
        print(f"  Total Welfare:        ${metrics['total_welfare']:,.2f}")
        print(f"  Optimal Welfare:      ${metrics['optimal_welfare']:,.2f}")
        print(f"  Efficiency Gap:       {metrics['efficiency_gap']*100:.2f}%")
        print(f"  Revenue:              ${metrics['revenue']:,.2f}")
        print(f"  Allocation Rate:      {metrics['allocation_rate']*100:.1f}%")
        print(f"  Capacity Utilization: {metrics['capacity_utilization']*100:.1f}%")
        
        print(f"\nPricing Metrics:")
        print(f"  Average Clearing Price: ${metrics['average_clearing_price']:.2f}")
        price_dist = metrics['price_distribution']
        print(f"  Price Range:            ${price_dist['min']:.2f} - ${price_dist['max']:.2f}")
        
        if verbose:
            print(f"\nAllocations:")
            for student_id, course_id in report['allocations'].items():
                price = report['clearing_prices'].get(student_id, 0)
                print(f"  {student_id} -> {course_id} (${price:.2f})")
    
    print("\n" + "="*60 + "\n")


def main():
    """Main entry point for simulation."""
    parser = argparse.ArgumentParser(
        description="Run hybrid auction simulations for course allocation"
    )
    parser.add_argument(
        '-n', '--students', type=int, default=20,
        help='Number of students (default: 20)'
    )
    parser.add_argument(
        '-m', '--courses', type=int, default=5,
        help='Number of courses (default: 5)'
    )
    parser.add_argument(
        '-r', '--runs', type=int, default=1,
        help='Number of simulation runs (default: 1)'
    )
    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help='Print detailed allocation info'
    )
    parser.add_argument(
        '-o', '--output', type=str,
        help='Output file for results (JSON)'
    )
    parser.add_argument(
        '--seed', type=int,
        help='Random seed for reproducibility'
    )
    parser.add_argument(
        '-c', '--compare', action='store_true',
        help='Compare auction vs RSD (random serial dictatorship)'
    )
    
    args = parser.parse_args()
    
    if args.compare:
        # Run comparison mode
        result = run_comparison(
            n_students=args.students,
            n_courses=args.courses,
            n_runs=args.runs
        )
        print_comparison_report(result)
    elif args.runs == 1:
        # Single run
        result = run_single_auction(
            n_students=args.students,
            n_courses=args.courses,
            random_seed=args.seed
        )
        print_report(result, verbose=args.verbose)
    else:
        # Batch run
        result = run_batch_simulation(
            n_students=args.students,
            n_courses=args.courses,
            n_runs=args.runs
        )
        print_report(result, verbose=args.verbose)
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"Results saved to {args.output}")


# =============================================================================
# Comparison Functions: Auction vs RSD
# =============================================================================

def run_comparison(
    n_students: int,
    n_courses: int,
    n_runs: int = 10,
    bids_per_student: tuple = (2, 5),
    random_seed: Optional[int] = None
) -> Dict:
    """
    Run both auction and RSD mechanisms and compare results.
    
    Uses the same underlying data (students, courses, bids) for fair comparison.
    """
    if random_seed is not None:
        random.seed(random_seed)
    
    all_results = []
    
    for i in range(n_runs):
        seed = random.randint(1, 100000)
        
        # Run Hybrid Auction
        auction = HybridAuction(random_seed=seed)
        auction.generate_students(n_students)
        courses = create_default_courses(n_courses)
        auction.generate_courses(courses)
        auction.generate_bids(bids_per_student=bids_per_student)
        
        auction_result = auction.allocate()
        auction_calculator = EfficiencyCalculator(
            auction.students, auction.courses, auction.bids
        )
        auction_metrics = auction_calculator.get_full_report(auction_result)
        
        # Run RSD with SAME data (reuse students, courses, bids)
        rsd = RandomSerialDictatorship(random_seed=seed)
        rsd.students = auction.students
        rsd.courses = {cid: Course(
            id=c.id, name=c.name, capacity=c.capacity, reserve_price=c.reserve_price
        ) for cid, c in auction.courses.items()}
        rsd.bids = [Bid(
            student_id=b.student_id,
            course_id=b.course_id,
            bid_amount=b.bid_amount,
            true_valuation=b.true_valuation
        ) for b in auction.bids]
        
        # Use seniority-based priority (seniors go before juniors)
        rsd_result = rsd.allocate(use_seniority_priority=True)
        
        # Calculate RSD metrics
        rsd_welfare = rsd_result.total_welfare
        rsd_allocation_rate = len(rsd_result.allocations) / len(rsd.students)
        rsd_capacity_util = sum(len(c.enrolled_students) for c in rsd.courses.values()) / sum(c.capacity for c in rsd.courses.values())
        
        # Calculate priority-weighted welfare for both mechanisms
        # For RSD: sum of (student priority weight * their course valuation)
        rsd_priority_welfare = 0.0
        for sid, course_id in rsd_result.allocations.items():
            for b in auction.bids:
                if b.student_id == sid and b.course_id == course_id:
                    rsd_priority_welfare += auction.students[sid].priority_weight * b.true_valuation
                    break
        
        all_results.append({
            'run': i + 1,
            'seed': seed,
            'auction': {
                'welfare': auction_metrics['total_welfare'],
                'priority_weighted_welfare': auction_metrics.get('priority_weighted_welfare', 0),
                'optimal_welfare': auction_metrics['optimal_welfare'],
                'efficiency_gap': auction_metrics['efficiency_gap'],
                'revenue': auction_metrics['revenue'],
                'allocation_rate': auction_metrics['allocation_rate'],
                'capacity_utilization': auction_metrics['capacity_utilization']
            },
            'rsd': {
                'welfare': rsd_welfare,
                'priority_weighted_welfare': rsd_priority_welfare,
                'allocation_rate': rsd_allocation_rate,
                'capacity_utilization': rsd_capacity_util
            }
        })
    
    # Aggregate results
    return _aggregate_comparison(all_results)


def _aggregate_comparison(results: List[Dict]) -> Dict:
    """Aggregate comparison results across multiple runs."""
    auction_welfare = [r['auction']['welfare'] for r in results]
    rsd_welfare = [r['rsd']['welfare'] for r in results]
    auction_priority_welfare = [r['auction'].get('priority_weighted_welfare', 0) for r in results]
    rsd_priority_welfare = [r['rsd'].get('priority_weighted_welfare', 0) for r in results]
    auction_efficiency = [1 - r['auction']['efficiency_gap'] for r in results]
    auction_revenue = [r['auction']['revenue'] for r in results]
    auction_allocation = [r['auction']['allocation_rate'] for r in results]
    rsd_allocation = [r['rsd']['allocation_rate'] for r in results]
    
    return {
        'parameters': {
            'n_runs': len(results)
        },
        'auction': {
            'welfare': _stats(auction_welfare),
            'priority_weighted_welfare': _stats(auction_priority_welfare),
            'efficiency': _stats(auction_efficiency),
            'revenue': _stats(auction_revenue),
            'allocation_rate': _stats(auction_allocation)
        },
        'rsd': {
            'welfare': _stats(rsd_welfare),
            'priority_weighted_welfare': _stats(rsd_priority_welfare),
            'allocation_rate': _stats(rsd_allocation)
        },
        'comparison': {
            'welfare_diff_mean': np.mean([a - r for a, r in zip(auction_welfare, rsd_welfare)]),
            'welfare_pct_improvement': np.mean([(a - r) / r * 100 if r > 0 else 0 for a, r in zip(auction_welfare, rsd_welfare)]),
            'priority_welfare_diff_mean': np.mean([a - r for a, r in zip(auction_priority_welfare, rsd_priority_welfare)]),
            'priority_welfare_pct_improvement': np.mean([(a - r) / r * 100 if r > 0 else 0 for a, r in zip(auction_priority_welfare, rsd_priority_welfare)]),
            'allocation_diff_mean': np.mean([a - r for a, r in zip(auction_allocation, rsd_allocation)])
        },
        'individual_results': results
    }


def _stats(values: List[float]) -> Dict:
    """Compute statistics for a list of values."""
    return {
        'mean': np.mean(values),
        'std': np.std(values),
        'min': np.min(values),
        'max': np.max(values)
    }


def print_comparison_report(report: Dict):
    """Print a formatted comparison report."""
    print("\n" + "="*70)
    print("MECHANISM COMPARISON: AUCTION vs RANDOM SERIAL DICTATORSHIP")
    print("="*70)
    print(f"\nRuns: {report['parameters']['n_runs']}")
    
    print("\n" + "-"*70)
    print("AUCTION MECHANISM")
    print("-"*70)
    a = report['auction']
    print(f"  Total Welfare:              ${a['welfare']['mean']:,.0f} ± ${a['welfare']['std']:,.0f}")
    print(f"  Priority-Weighted Welfare: ${a['priority_weighted_welfare']['mean']:,.0f} ± ${a['priority_weighted_welfare']['std']:,.0f}")
    print(f"  Efficiency:                 {a['efficiency']['mean']*100:.1f}% ± {a['efficiency']['std']*100:.1f}%")
    print(f"  Revenue:                    ${a['revenue']['mean']:,.0f} ± ${a['revenue']['std']:,.0f}")
    print(f"  Allocation Rate:            {a['allocation_rate']['mean']*100:.1f}% ± {a['allocation_rate']['std']*100:.1f}%")
    
    print("\n" + "-"*70)
    print("RANDOM SERIAL DICTATORSHIP (Current System with Seniority)")
    print("-"*70)
    r = report['rsd']
    print(f"  Total Welfare:              ${r['welfare']['mean']:,.0f} ± ${r['welfare']['std']:,.0f}")
    print(f"  Priority-Weighted Welfare:  ${r['priority_weighted_welfare']['mean']:,.0f} ± ${r['priority_weighted_welfare']['std']:,.0f}")
    print(f"  Allocation Rate:            {r['allocation_rate']['mean']*100:.1f}% ± {r['allocation_rate']['std']*100:.1f}%")
    
    print("\n" + "-"*70)
    print("COMPARISON SUMMARY")
    print("-"*70)
    c = report['comparison']
    print(f"  Raw Welfare Δ:              ${c['welfare_diff_mean']:,.0f} (avg)")
    print(f"  Raw Welfare Change:          {c['welfare_pct_improvement']:.1f}%")
    print(f"  Priority-Weighted Δ:         ${c['priority_welfare_diff_mean']:,.0f} (avg)")
    print(f"  Priority-Weighted Change:    {c['priority_welfare_pct_improvement']:.1f}%")
    print(f"  Allocation Rate Δ:           {c['allocation_diff_mean']*100:+.1f}%")
    
    print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    main()