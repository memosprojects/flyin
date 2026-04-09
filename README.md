*This project has been created as part of the 42 curriculum by mehdemir.*

# Flyin

## Description

Flyin is a Python simulation project that routes multiple drones through a network of interconnected hubs while minimizing the total number of turns required to deliver all drones from a start hub to an end hub.

Each map defines hubs, coordinates, zone types, capacities, and bidirectional connections. The system parses this input, builds a graph, computes routes, schedules movements turn by turn, and visualizes the simulation.

This problem goes beyond a classic shortest path problem. It requires coordinating multiple agents under strict movement, timing, and capacity constraints while keeping the total simulation time as low as possible.

## Features

* Strict parser with validation and clear error reporting
* Object oriented models for hubs, connections, and drones
* Time aware pathfinding with scheduling constraints
* Turn based simulation engine
* Support for normal, restricted, priority, and blocked zones
* Capacity aware routing for hubs and connections
* Graphical visualization of simulation state
* Terminal output compliant with project specifications
* Type safety with mypy and style compliance with flake8

## Instructions

### Requirements

* Python 3.10+
* make

### Installation

```bash
make install
```

### Run

```bash
make run
```

### Debug

```bash
make debug
```

### Lint

```bash
make lint
```

### Strict Lint

```bash
make lint-strict
```

### Clean

```bash
make clean
```

## Input Format

The program expects a map file describing drones, hubs, and connections following the project specification.

Example:

```text
nb_drones: 5
start_hub: hub 0 0
end_hub: goal 10 10
hub: roof1 3 4 [zone=restricted]
hub: roof2 6 2 [zone=normal]
connection: hub-roof1
connection: roof1-roof2
connection: roof2-goal
```

### Running with Custom Maps

To use a custom map:

* Place the map file inside the expected maps directory with the correct naming convention
* Run:

```bash
make run
```

The application automatically detects available maps and includes the new map in the welcome screen.

Note:

* The UI is not fully dynamically adapted for arbitrary new maps
* Visual layout or scaling may be slightly disrupted
* The simulation logic remains functional for at least one additional custom map

## Usage

The program loads a map, validates it, computes routes, and starts a graphical simulation.

The interface allows:

* Step by step turn progression
* Visualization of drone movement
* Inspection of hub capacities and types
* Toggle of hub name labels
* Real time simulation tracking

## Algorithm Choices and Implementation Strategy

The routing logic is implemented in `algorithm.py` via the `DronePlanner` class.

This problem is a multi agent pathfinding problem under constraints. The solution combines time aware search with resource reservation.

### Core Approach

The algorithm uses a sequential reservation based planning strategy:

1. Drones are planned one by one
2. Each drone computes a feasible route using time aware search
3. The route reserves hubs and connections across time
4. Subsequent drones adapt to existing reservations

This creates implicit coordination without requiring a global optimization step.

### Time Aware Search

The search operates on an expanded state space:

```text
(hub, current_turn, previous_hub)
```

This enables:

* Explicit time reasoning
* Conflict avoidance
* Multi turn movement handling
* Scheduling decisions

### Movement Model

Each turn, a drone can:

**Wait**

* Stay in place if capacity allows

**Move**

* Transition to a connected hub if:

  * Hub capacity is available
  * Connection capacity is available

Traversal costs:

* Normal and priority zones: 1 turn
* Restricted zones: 2 turns
* Blocked zones: not traversable

### Cost Function

The algorithm uses a lexicographic objective:

```text
(total_time, -priority_visits)
```

This means:

* The primary objective is to minimize total arrival time
* Among equally fast routes, paths through priority zones are preferred

### Reservation Mechanism

After computing a path:

* Hubs are reserved per turn
* Connections are reserved during traversal

Tracked using:

```text
hub_usage[turn][hub]
edge_usage[turn][edge]
```

This guarantees:

* No capacity violations
* No collisions
* Valid scheduling

### Emergent Behavior

* Early drones take the most efficient available paths
* Later drones adapt dynamically to congestion
* Bottlenecks are handled through waiting or rerouting
* The system distributes traffic across available routes

## Complexity Analysis

The algorithm operates on a time expanded graph.

### Time Complexity

Per drone:

```text
O((V × T) log (V × T))
```

Where:

* `V` is the number of hubs
* `T` is the time horizon

Total complexity:

```text
O(D × (V × T) log (V × T))
```

Where:

* `D` is the number of drones

### Memory Complexity

* Hub reservations: `O(T × V)`
* Edge reservations: `O(T × E)`

### Trade Offs

* Sequential planning reduces computational complexity
* It avoids the exponential cost of full joint multi agent planning
* It sacrifices global optimality in favor of simplicity, determinism, and traceability

## Performance

The implementation satisfies all reference benchmarks defined in the project specification.

### Results

* Easy maps: solved within optimal turn limits
* Medium maps: solved within target ranges
* Hard maps: solved within required bounds
* Overall: perfect benchmark satisfaction

### Observations

* The algorithm distributes drones efficiently across multiple paths
* Bottlenecks are handled through waiting and reservation aware routing
* Restricted zones are integrated correctly into movement scheduling
* The implementation maintains strong throughput under capacity constraints

## Error Handling

The system includes strict validation and runtime safeguards.

### Parser Validation

The parser enforces:

* Exactly one start hub and one end hub
* Unique hub names
* Valid integer coordinates
* Valid zone types
* Proper connection definitions
* No duplicate connections
* Positive capacity values

### Failure Handling

* Invalid input stops execution immediately
* Clear error messages report the cause and location of the issue

### Runtime Safety

* Try except blocks are used to avoid unexpected crashes
* Invalid simulation states are prevented through strict pre validation
* Resource conflicts are prevented through reservation checks

## Testing

Custom test scenarios were created to validate correctness and robustness.

### Covered Cases

* Capacity conflicts
* Deadlocks and congestion
* Multi turn restricted traversal
* Path distribution across multiple routes
* Parser edge cases and invalid inputs

### Approach

* Manual simulation verification
* Output validation against the required format
* Stress testing with increasing drone counts

## Visual Representation

The GUI provides:

* Hub positions based on map coordinates
* Connection layout between hubs
* Drone positions for each turn
* Zone type indicators
* Hub capacity overlays
* Turn tracking
* Toggleable hub names

This visual representation improves debugging and makes the scheduling logic easier to understand during simulation.

## Terminal Output

Each line represents one simulation turn:

```text
D1-A D2-B
D1-C
```

* Only moving drones are shown
* Drones that reach the destination are removed from further output
* The simulation ends when all drones have reached the goal

## Project Structure

```text
.
├── Makefile
├── README.md
├── bin
│   ├── Units.py
│   ├── algorithm.py
│   ├── main.py
│   ├── mappage.py
│   ├── parser.py
│   └── welcomepage.py
└── uilibrary
```

## Resources

### References

* Python documentation
* Arcade library documentation
* Pydantic documentation
* mypy documentation
* flake8 documentation
* Graph pathfinding and scheduling concepts
* Kenney UI Pack Pixel Adventure: https://kenney.nl/assets/ui-pack-pixel-adventure
* Dungeon tiles by Buch: http://blog-buch.rhcloud.com
* The background image used in this project was found online without clear source information. I tried to identify the original creator but could not verify the origin. If you are the creator of this image, please contact me so that proper credit can be added.

### AI Usage

AI was used for:

* Debugging type errors and lint issues
* Reviewing code structure
* Refining UI logic
* Improving documentation clarity

All generated outputs were reviewed, validated, and adapted before use.

## Limitations

* Sequential planning is not globally optimal
* No dynamic rerouting after initial planning
* No parallel multi agent optimization
* Performance depends on planning order in congested maps

