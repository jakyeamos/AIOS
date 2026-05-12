# Entropy Tracking

Entropy tracking asks whether AIOS is over-converging.

Track:

- repeated candidate shapes
- repeated judge sets
- repeated recommendation structure
- too little novelty
- too much safe convergence

Current heuristic:

- diversity score = unique candidate formulations / total candidate formulations
- novelty score = candidate diversity plus judge-role diversity

Scores are heuristic and must be labeled as such in UI and reports.
