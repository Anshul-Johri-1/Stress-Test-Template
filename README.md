# StressTest

Find the test that breaks your solution, by comparing it against a brute force on thousands of random inputs.

## What's in here

```
StressTest/
├── wrong.cpp       your solution (the one that gets WA)
├── correct.cpp     a brute force you trust (slow is fine)
├── generator.cpp   prints one random test; lots of helpers inside
├── checker.cpp     only for problems with many valid answers (./run.sh -c)
├── run.sh          the only command you need
├── tools/          the engine behind run.sh (you never need to open it)
└── fail/           appears when a test fails: input, expected, received, debug output
```

## How to use it

1. Paste your solution into `wrong.cpp` and a brute force into `correct.cpp`.
2. Write `main()` in `generator.cpp` so it prints one small random input.
3. Run it:
   ```bash
   ./run.sh
   ```
4. If a test fails, you see the input, the expected and received output, and your `debug()` prints. Fix your code, then check it on that same test:
   ```bash
   ./run.sh -f
   ```
5. Done with the problem? Get the blank files back:
   ```bash
   git restore .
   ```

C++ or Python both work: name the file `correct.py`, `wrong.py`, etc. If both exist, the one you edited last is used.

## Options

| Command | What it does |
|---|---|
| `./run.sh 200` | run 200 tests (default 5000) |
| `./run.sh -t 1` | time limit of 1s for `wrong` (default 2s) |
| `./run.sh -e 1e-6` | accept floating-point answers within 1e-6 |
| `./run.sh -i` | ignore case (`YES` == `yes`) |
| `./run.sh -c` | judge with `checker.cpp` instead of comparing outputs |
| `./run.sh -m 500` | after a failure, keep looking for a smaller failing test |
| `./run.sh -f` | re-run the last failing test (`./run.sh -f my.txt` for any file) |
| `./run.sh -s SEED 1` | re-create one test from the seed shown in the report |
| `./run.sh -- 100` | pass `100` to the generator (read it as `argv[2]`) |
| `./run.sh -q` | don't show the first-test preview |
| `./run.sh -h` | show all of this in the terminal |

## What you get when a test fails

- **The verdict:** Wrong Answer (with the first differing value marked), Runtime Error (with a hint like "assert failed" or "out-of-bounds"), or Time Limit Exceeded.
- **The smallest failing input** that was found, saved in `fail/` so you can open it.
- **Your `debug()` output.** `wrong.cpp` is re-run on the failing test with debugging on and bounds-checked vectors, so a hidden out-of-bounds access gets caught.
- **A warning** if `correct.cpp` printed nothing, which usually means the brute force wasn't pasted in yet.

Tests run in parallel and binaries are only rebuilt when the code changes, so a run takes seconds.

## Generator helpers

All of these are explained, with examples, at the top of `generator.cpp`.

```cpp
rand(l, r)                     // random integer in [l, r]
prob(1, 4)                     // true 1 time in 4
pick(vi{3, 10, 1000000000})    // random element of a list
array_random(n, l, r)          // n random values
array_perm(n)                  // permutation of 1..n
array_distinct(n, l, r)        // n different values
array_partition(sum, k)        // k positive parts adding up to sum
str_random(n, "ab")            // random string
grid_random(n, m, ".#")        // random grid
tree_random(n, PATH)           // tree edges (RANDOM, PATH, STAR, DEEP, BINARY)
graph_random(n, m, true)       // connected simple graph
print_edges(edges)             // prints "u v" per edge
```

## Checker (only with `-c`)

For problems where many answers are correct. `checker.cpp` gets the input, the brute force's output and your output. Call `wa("reason")` to reject an answer. If it reaches the end, the answer is accepted.
