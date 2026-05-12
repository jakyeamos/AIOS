# Entropy Tracking

Entropy tracking records whether AIOS is becoming too repetitive in strategy work.

The current workflow stores observations in `entropy_observations`:

- repeated candidate shapes
- repeated judges
- repeated candidate formulations
- novelty score
- diversity score
- recommendation

Current formula:

- diversity score = unique candidate formulations / total candidate formulations
- novelty score = candidate diversity plus judge-role diversity

These are heuristic scores. UI and reports must say how they were calculated and what the operator should inspect next.

Entropy signals should influence prompt and skill promotion. A pattern with low diversity should not become active without stronger evidence.
