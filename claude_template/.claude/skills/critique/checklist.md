# Review checklist (≤ 12 items; BLOCKING = wrong, unsafe, unrunnable, or violates a stated requirement)

1. Does the change do what was asked, all of it, and nothing that was not asked?
2. Is every claim of "tested" or "verified" backed by a command and its output?
3. What input, state, or ordering breaks it? Name one concrete case.
4. Are errors handled where they can occur, and never swallowed silently?
5. Does anything leak secrets, write outside its intended paths, or run with more
   privilege than needed?
6. Are names, types, and interfaces consistent with the surrounding code?
7. Is there dead code, leftover debug output, a TODO, or a disabled test?
8. Does it duplicate something that already exists in the repo?
9. Would a reader with no context understand why, not just what? (One comment where the
   why is non-obvious; no narration.)
10. Does the diff touch files it did not need to touch?
11. For documents: are numbers internally consistent, and are references to sections,
    files, and commands real?
12. Is the smallest correct change being made, or is it over-engineered?
