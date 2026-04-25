# Hajj Traffic Management System

### CS3081 – Artificial Intelligence | Effat University | Spring 2026

**Supervisor:** Dr. Naila Marir

---

## Overview

A multi-agent simulation of an intelligent traffic management subsystem for Hajj, the annual Islamic pilgrimage to Mecca. The system models four cooperative agents that monitor road conditions, control traffic signals, navigate vehicles, and prioritize emergency responders — all operating under real-world adversarial conditions such as sensor noise, incomplete knowledge, and multi-agent conflict.

---

## Agents

| Agent              | AI Technique                  | Adversarial Challenge                    |
| ------------------ | ----------------------------- | ---------------------------------------- |
| Road Agent         | A\*, Probabilistic (Bayesian) | Noisy sensor readings                    |
| Intersection Agent | CSP, Signal Control           | Emergency override vs. fair scheduling   |
| Vehicle Agent      | A\*, BDI                      | Incomplete road knowledge                |
| Emergency Agent    | Rule-Based Reasoning          | Signal conflicts, slow corridor clearing |

---

## Team

| Member | Role               | Agent                |
| ------ | ------------------ | -------------------- |
| Yousef | Integration Lead   | Road Agent           |
| Zaid   | Intersection Agent | CSP signal control   |
| Rahil  | Vehicle Agent      | A\* navigation, BDI  |
| Firas  | Emergency Agent    | Priority pre-emption |

---

## Installation

```bash
git clone https://github.com/skuwii/hajj_traffic.git
cd hajj_traffic
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the Simulation

```bash
python simulation.py
```

This runs 100 ticks with 10 vehicle agents and 1 emergency agent, displays a live visualization, and shows a results summary on completion.

## Running Tests

```bash
python tests/test_road.py
python tests/test_intersection.py
python tests/test_vehicle.py
python tests/test_emergency.py
```

---

## Tech Stack

| Purpose              | Tool                                |
| -------------------- | ----------------------------------- |
| Agent simulation     | Mesa 3.x                            |
| Road graph & routing | NetworkX                            |
| Visualization        | Matplotlib                          |
| Agent messaging      | Custom message bus (FIPA-ACL style) |
| Version control      | GitHub                              |

---

## Repository Structure

hajj_traffic/
├── agents/ # Four agent implementations
├── core/ # Road graph, message bus, environment
├── utils/ # A\*, CSP solver, probabilistic helpers
├── tests/ # Unit tests per agent
├── simulation.py # Main entry point
└── visualize.py # Live dashboard

---

_CS3081 – Artificial Intelligence | Effat University | Spring 2026_
