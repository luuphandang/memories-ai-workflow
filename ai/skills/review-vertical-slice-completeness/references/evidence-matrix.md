# Evidence matrix

Build one row per effective acceptance criterion:

| Criterion | Slice | Implementation | Wiring/runtime path | Test | Validation | Result |
|---|---|---|---|---|---|---|

Evidence must name concrete files, symbols, test cases or command results. A handoff statement without matching diff/test evidence is not sufficient. For shared infrastructure, point to the exact consumer path proving the current feature uses it.

For a large plan, one handoff entry named `slice:<slice-id>` may cover all criteria in that slice when its evidence explicitly summarizes the complete slice and its verification. Use criterion-level entries for failures, waivers or criteria needing distinct evidence.
