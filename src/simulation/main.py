"""Simulation runner for hybrid auction experiments."""

import argparse
import json
import random
from typing import Dict, List, Optional
from dataclasses import asdict
import numpy as np

from ..auction.hybrid_auction import HybridAuction
from ..analysis.metrics import EfficiencyCalculator


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
    
    args = parser.parse_args()
    
    if args.runs == 1:
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


if __name__ == '__main__':
    main()