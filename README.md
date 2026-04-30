# auction_course_reg

Auction Design for Course Enrollment, specifically tailored to UVA in hopes of better optimizing student utility.

## Running the Simulation

This repository provides a hybrid auction simulation for allocating students to courses.

### Install dependencies

From the project root:

```bash
python -m pip install -r requirements.txt
```

### Run the simulation

The main entrypoint is `src/simulation/main.py` and can be executed with:

```bash
python -m src.simulation.main
```

### Command-line parameters

- `-n`, `--students`: Number of students (default: `20`)
- `-m`, `--courses`: Number of courses (default: `5`)
- `-r`, `--runs`: Number of simulation runs (default: `1`)
- `-v`, `--verbose`: Print detailed allocation information
- `-o`, `--output`: Output file for results in JSON format
- `--seed`: Random seed for reproducibility

Example:

```bash
python -m src.simulation.main --students 20 --courses 5 --runs 1 --verbose --output results.json
```

## Output explanation

The simulation prints a report with the following sections:

- `Parameters`: Inputs used for the simulation, including number of students, courses, and runs.
- `Efficiency Metrics`: Measures the quality of the auction outcome.
  - `Total Welfare`: Sum of values for allocated students based on their valuations.
  - `Optimal Welfare`: Estimated maximum welfare if allocation were perfectly optimized.
  - `Efficiency Gap`: The percentage shortfall between actual and optimal welfare.
  - `Revenue`: Total clearing price revenue collected from allocated students.
  - `Allocation Rate`: Fraction of students who received a course.
  - `Capacity Utilization`: Share of total course capacity that was filled.
- `Pricing Metrics`: Describes the clearing prices charged.
  - `Average Clearing Price`: Mean price paid by allocated students.
  - `Price Range`: Minimum and maximum clearing prices observed.

When `--runs` is greater than `1`, the output is aggregated across multiple simulation runs and shows mean, standard deviation, minimum, and maximum values for each metric.
