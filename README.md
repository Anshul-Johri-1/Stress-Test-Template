# StressTest

Paste the brute force into `correct.cpp`, your solution into `wrong.cpp`, write `generator.cpp`, then:

```bash
./run.sh
```

Tests run in parallel on all cores and stop at the first failure. The failing test is saved to
`input.txt` / `expected_output.txt` / `received_output.txt`.

The committed versions of the four files are blank templates. When you're done with a problem:

```bash
git restore .
```

## Cheat sheet

| Command | What it does |
|---|---|
| `./run.sh 200` | run 200 tests (default 5000) |
| `./run.sh -t 1` | 1s CPU time limit for wrong (default 2s; the brute gets max(5s, 5×)) |
| `./run.sh -e 1e-6` | compare floats with abs/rel tolerance |
| `./run.sh -i` | case-insensitive (`YES` == `yes`) |
| `./run.sh -c` | judge with `checker.cpp` (multiple valid answers) |
| `./run.sh -m 500` | after a failure, run 500 more tests and show the smallest failing input |
| `./run.sh -f input.txt` | re-run once on a saved input (check your fix) |
| `./run.sh -s SEED 1` | reproduce one test from its seed |
| `./run.sh -- 100 5` | pass `100 5` to the generator as `argv[2]`, `argv[3]` |
| `./run.sh -q` | skip the first-test preview |
| `./run.sh -j 1` | one test at a time |

## What it does for you

- **Rebuilds only what changed.** Binaries are cached by content hash, and `<bits/stdc++.h>` is precompiled.
- **Python works too.** If both `correct.py` and `correct.cpp` exist, the one you edited last is used. Same for wrong, generator and checker.
- **Verdicts:** WA (shows the first differing token, with the line marked), RE (signal plus a hint, e.g. assert or out of bounds), and TLE (CPU time, so parallel load doesn't cause false TLEs). If the generator, brute or checker crashes, it says so.
- **Debug re-run on failure.** `wrong.cpp` is rebuilt without `ONLINE_JUDGE` and with `_GLIBCXX_DEBUG`, then run on the failing input. You see your `debug()` output (saved to `debug_log.txt`) and out-of-bounds accesses that only showed up as a wrong answer at `-O2`. It also warns if the debug build prints a different answer, which usually means undefined behaviour.
- **256 MB stack**, like Codeforces, so deep DFS doesn't segfault locally.
- **Sanity warnings:** brute printed nothing, or correct and wrong are identical.
- **No brute?** Delete `correct.cpp` to check `wrong` only for crashes and TLE. Add `-c` to have a checker validate the output.

## Generator (`generator.cpp`)

Each test's seed is passed as `argv[1]`, so every failure is reproducible.

```cpp
rand(l, r)                    // inclusive, 64-bit, uniform (rand(1, 1e18) works)
rand_real(l, r), prob(a, b), pick(vec)
array_random(n, l, r)         // array_random<ll>(n, 1, 1e18) for long long
array_perm(n, start = 1)
array_distinct(n, l, r)
array_partition(sum, k, mn=1) // k parts >= mn summing to sum (split "sum of n" across tests)
str_random(n, "abc"), grid_random(n, m, ".#")
tree_random(n, RANDOM|PATH|STAR|DEEP|BINARY)   // shuffled edges, 1-indexed
tree_parents(n, type)         // p_2..p_n with p_i < i
graph_random(n, m, connected) // simple graph
print_edges(edges)
```

## Checker (`checker.cpp`)

Called as `checker input expected received`. Exit 0 means accepted. Otherwise call `wa("reason", ...)`.
Use `read<T>("what")` to read the contestant's output safely, and `expect_eof()` to reject extra output.
