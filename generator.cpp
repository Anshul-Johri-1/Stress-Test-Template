// =====================================================================================
// generator.cpp: prints ONE random test to stdout. run.sh calls it once per test.
//
//   ./generator SEED [extra args...]
//
// SEED (argv[1]) is different for every test and decides every random number below,
// so the same seed always prints the same test. That is how `./run.sh -s SEED 1`
// reproduces a failure. Extra args come from `./run.sh -- a b c` (argv[2], argv[3], ...).
//
// Writing a good generator:
//   1. Keep tests SMALL (n around 1..10). The brute force must stay fast, small
//      counterexamples are easy to trace by hand, and nearly every bug shows up on them.
//   2. Use SMALL VALUES too (0..3, 1..10). Many ties and duplicates catch the
//      "== vs <", "lower_bound vs upper_bound" and "forgot duplicates" bugs.
//   3. Sometimes use the REAL LIMITS for values (1e9, 1e18) to catch overflow.
//   4. Hit the EDGES of every constraint: n = 1, k = 0, k = n, all values equal...
//   5. Print in exactly the input format of the problem. Run ./run.sh once and look at
//      the "First test" preview to check it.
// =====================================================================================
#include <bits/stdc++.h>
using namespace std;

#include "Debug.cpp"

/* clang-format off */
#define FOR1(a) for (int __ = 0; __ < int(a); __++)
#define FOR2(i, a) for (int i = 0; i < int(a); i++)
#define FOR3(i, a, b) for (int i = a; i < int(b); i++)
#define overload(a, b, c, d, ...) d
#define FOR(...) overload(__VA_ARGS__, FOR3, FOR2, FOR1)(__VA_ARGS__)
#define all(x) x.begin(), x.end()
template <typename T, typename... V> void out(const T &x, const V &...tail) { cout << x; if constexpr (sizeof...(tail)) cout << ' ', out(tail...); else cout << '\n'; } template <typename T> void out(const vector<T> &vec) { int i = 0; for (const auto &x : vec) cout << (i++ ? " " : "") << x; cout << '\n'; }
using ll = long long;
using vi = vector<int>;
using vvi = vector<vector<int>>;
using pii = pair<int, int>;
mt19937_64 mt;  // the random engine, seeded in main()
/* clang-format on */

// ---------------------------------------------------------------- random numbers
// Random integer in [l, r], both ends included. 64-bit, so rand(1, 1e18) works.
ll rand(ll l, ll r) { return uniform_int_distribution<ll>(l, r)(mt); }
// Random real number in [l, r).
double rand_real(double l, double r) { return uniform_real_distribution<double>(l, r)(mt); }
// True with probability a/b. Use for "sometimes": if (prob(1, 4)) k = 0;
bool prob(int a, int b) { return rand(1, b) <= a; }
// Random element of a list. Use to mix value ranges: int V = pick(vi{3, 10, 1000000000});
template <typename T>
T pick(const vector<T>& v) { return v[rand(0, int(v.size()) - 1)]; }

// ---------------------------------------------------------------- arrays
// n random values in [l, r]. Repeats allowed (a small range gives many duplicates).
//   array_random(5, 1, 3)        -> 2 1 3 3 1
//   array_random<ll>(n, 1, 1e18) -> vector<long long> for big values
template <typename T = int>
vector<T> array_random(int n, ll l, ll r) {
    vector<T> arr(n);
    for (T& x : arr)
        x = rand(l, r);
    return arr;
}
// The numbers start..start+n-1 in random order (a permutation).
//   array_perm(5)    -> 3 1 5 2 4   (1-indexed)
//   array_perm(5, 0) -> 2 0 4 1 3   (0-indexed)
template <typename T = int>
vector<T> array_perm(int n, T start = 1) {
    vector<T> arr(n);
    iota(all(arr), start);
    shuffle(all(arr), mt);
    return arr;
}
// n DIFFERENT values from [l, r], in random order. Needs r - l + 1 >= n.
//   array_distinct(3, 1, 10) -> 7 2 9
// Sort it if the problem wants a strictly increasing array.
template <typename T = int>
vector<T> array_distinct(int n, ll l, ll r) {
    assert(r - l + 1 >= n);
    vector<T> arr;
    if (r - l + 1 <= 4LL * n) {  // small range: shuffle the whole range, take n
        vector<T> all_vals(r - l + 1);
        iota(all(all_vals), T(l));
        shuffle(all(all_vals), mt);
        arr.assign(all_vals.begin(), all_vals.begin() + n);
    } else {  // big range: draw until we have n unused values
        set<T> seen;
        while ((int)arr.size() < n)
            if (T x = rand(l, r); seen.insert(x).second)
                arr.push_back(x);
    }
    return arr;
}
// k numbers, each >= mn, that add up to exactly `sum`.
//   array_partition(10, 3) -> 4 1 5
// Main use: "the sum of n over all test cases <= X". Split X into the n of each test:
//   for (int n : array_partition(20, t)) { ... }
template <typename T = int>
vector<T> array_partition(ll sum, int k, ll mn = 1) {
    assert(k >= 1 && sum >= mn * k);
    ll free = sum - mn * k;  // give every part mn first, then split the rest at random cut points
    vector<ll> cuts = {0, free};
    FOR(k - 1)
    cuts.push_back(rand(0, free));
    sort(all(cuts));
    vector<T> parts(k);
    FOR(i, k)
    parts[i] = mn + cuts[i + 1] - cuts[i];
    return parts;
}

// ---------------------------------------------------------------- strings & grids
// Random string of length n over the given letters. A small alphabet gives more
// repeats and palindromes, which usually catches more bugs.
//   str_random(6)               -> "abcaab"
//   str_random(6, "01")         -> "010011"  (binary string)
//   str_random(6, "()")         -> "(()))("  (NOT necessarily balanced)
string str_random(int n, const string& alphabet = "abc") {
    string s(n, ' ');
    for (char& ch : s)
        ch = alphabet[rand(0, int(alphabet.size()) - 1)];
    return s;
}
// n rows of m characters. Print with: for (auto& row : g) out(row);
//   grid_random(2, 4)        -> ".#..", "##.#"
//   grid_random(3, 3, "...#") -> mostly free cells (repeat a character to make it likelier)
vector<string> grid_random(int n, int m, const string& alphabet = ".#") {
    vector<string> g(n);
    for (auto& row : g)
        row = str_random(m, alphabet);
    return g;
}

// ---------------------------------------------------------------- trees & graphs (vertices 1..n)
// Tree shapes. Random trees are shallow, so also try the extreme shapes:
//   RANDOM  every vertex hangs off a random earlier vertex (depth about log n)
//   PATH    a single chain, the deepest tree (recursion depth, worst-case paths)
//   STAR    one center joined to everyone (max degree)
//   DEEP    random but long and thin (each parent is among the 3 previous vertices)
//   BINARY  a complete binary tree
enum TreeType { RANDOM,
                PATH,
                STAR,
                DEEP,
                BINARY };
// Internal helper: parent[i] < i for i in [1, n), 0-indexed, before relabelling.
vector<int> tree_shape(int n, TreeType type) {
    vector<int> par(n, -1);
    FOR(i, 1, n)
    switch (type) {
        case PATH:
            par[i] = i - 1;
            break;
        case STAR:
            par[i] = 0;
            break;
        case DEEP:
            par[i] = rand(max(0, i - 3), i - 1);
            break;
        case BINARY:
            par[i] = (i - 1) / 2;
            break;
        default:
            par[i] = rand(0, i - 1);
    }
    return par;
}
// n-1 edges "u v" of a tree on vertices 1..n. Labels, edge order and the direction of
// each edge are all shuffled, so a PATH isn't simply 1-2-3-...
//   print_edges(tree_random(n));
//   print_edges(tree_random(n, PATH));
vector<pii> tree_random(int n, TreeType type = RANDOM) {
    vector<int> par = tree_shape(n, type), label = array_perm(n);
    vector<pii> edges;
    FOR(i, 1, n) {
        int u = label[i], v = label[par[i]];
        if (prob(1, 2))
            swap(u, v);
        edges.push_back({u, v});
    }
    shuffle(all(edges), mt);
    return edges;
}
// Tree given as a parent list "p_2 p_3 ... p_n" with p_i < i (root is 1).
// Use when the input format is "the parent of each vertex": out(tree_parents(n));
vector<int> tree_parents(int n, TreeType type = RANDOM) {
    vector<int> par = tree_shape(n, type), p;
    FOR(i, 1, n)
    p.push_back(par[i] + 1);
    return p;
}
// Undirected graph with exactly m edges, no self-loops and no repeated edges.
// Needs m <= n(n-1)/2, and m >= n-1 if connected = true.
//   print_edges(graph_random(n, m));        // may be disconnected
//   print_edges(graph_random(n, m, true));  // guaranteed connected (built on a random tree)
// Weights: for (auto [u, v] : graph_random(n, m)) out(u, v, rand(1, 10));
vector<pii> graph_random(int n, int m, bool connected = false) {
    assert(m <= 1LL * n * (n - 1) / 2 && (!connected || m >= n - 1));
    set<pii> used;
    vector<pii> edges;
    auto add = [&](int u, int v) {
        if (u == v || used.count({min(u, v), max(u, v)}))
            return;
        used.insert({min(u, v), max(u, v)});
        edges.push_back({u, v});
    };
    if (connected)
        for (auto [u, v] : tree_random(n))
            add(u, v);
    while ((int)edges.size() < m)
        add(rand(1, n), rand(1, n));
    shuffle(all(edges), mt);
    return edges;
}
// Prints one "u v" line per edge.
void print_edges(const vector<pii>& edges) {
    for (auto [u, v] : edges)
        out(u, v);
}

// ---------------------------------------------------------------- main
signed main(int argc, char** argv) {
    // Seed from run.sh. Run by hand without an argument, it picks a random seed.
    mt.seed(argc > 1 ? atoll(argv[1]) : random_device{}());
    // Optional knob from `./run.sh -- 50`:  int MAXN = argc > 2 ? atoi(argv[2]) : 10;

    // Example: "t test cases, each: n, then n numbers". Replace with your problem's format.
    int t = 1;  // one case per test is easiest to debug; raise it to cover more per run
    out(t);
    FOR(t) {
        int n = rand(1, 10);
        out(n);
        out(array_random(n, 1, 10));
    }

    // Other common formats (copy what you need):
    //
    // Tree:            int n = rand(1, 8); out(n); print_edges(tree_random(n, TreeType(rand(0, 4))));
    // Graph:           int n = rand(2, 6), m = rand(n - 1, n * (n - 1) / 2);
    //                  out(n, m); print_edges(graph_random(n, m, true));
    // String:          out(str_random(rand(1, 8), "ab"));
    // Grid:            int n = rand(1, 4), m = rand(1, 4); out(n, m);
    //                  for (auto& row : grid_random(n, m)) out(row);
    // Queries:         int q = rand(1, 5); out(q);
    //                  FOR(q) { int l = rand(1, n), r = rand(l, n); out(l, r); }
    // Sum of n <= 20:  int t = rand(1, 4); out(t);
    //                  for (int n : array_partition(20, t)) { out(n); out(array_random(n, 1, 10)); }
    return 0;
}
