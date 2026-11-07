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
mt19937_64 mt;  // seeded from argv[1] in main(), so every test is reproducible from its seed
ll rand(ll l, ll r) { return uniform_int_distribution<ll>(l, r)(mt); }  // inclusive, no modulo bias, 64-bit safe
double rand_real(double l, double r) { return uniform_real_distribution<double>(l, r)(mt); }
bool prob(int a, int b) { return rand(1, b) <= a; }  // true with probability a/b
template <typename T> T pick(const vector<T> &v) { return v[rand(0, int(v.size()) - 1)]; }
/* clang-format on */

// ---------------------------------------------------------------- arrays
template <typename T = int>
vector<T> array_random(int n, ll l, ll r) {
    vector<T> arr(n);
    for (T& x : arr) x = rand(l, r);
    return arr;
}
template <typename T = int>
vector<T> array_perm(int n, T start = 1) {
    vector<T> arr(n);
    iota(all(arr), start);
    shuffle(all(arr), mt);
    return arr;
}
// n distinct values from [l, r]
template <typename T = int>
vector<T> array_distinct(int n, ll l, ll r) {
    assert(r - l + 1 >= n);
    vector<T> arr;
    if (r - l + 1 <= 4LL * n) {
        vector<T> all_vals(r - l + 1);
        iota(all(all_vals), T(l));
        shuffle(all(all_vals), mt);
        arr.assign(all_vals.begin(), all_vals.begin() + n);
    } else {
        set<T> seen;
        while ((int)arr.size() < n)
            if (T x = rand(l, r); seen.insert(x).second) arr.push_back(x);
    }
    return arr;
}
// k numbers, each >= mn, summing to exactly sum (e.g. split "sum of n over all tests")
template <typename T = int>
vector<T> array_partition(ll sum, int k, ll mn = 1) {
    assert(k >= 1 && sum >= mn * k);
    ll free = sum - mn * k;
    vector<ll> cuts = {0, free};
    FOR(k - 1) cuts.push_back(rand(0, free));
    sort(all(cuts));
    vector<T> parts(k);
    FOR(i, k) parts[i] = mn + cuts[i + 1] - cuts[i];
    return parts;
}

// ---------------------------------------------------------------- strings
string str_random(int n, const string& alphabet = "abc") {
    string s(n, ' ');
    for (char& ch : s) ch = alphabet[rand(0, int(alphabet.size()) - 1)];
    return s;
}
vector<string> grid_random(int n, int m, const string& alphabet = ".#") {
    vector<string> g(n);
    for (auto& row : g) row = str_random(m, alphabet);
    return g;
}

// ---------------------------------------------------------------- trees & graphs (1-indexed)
enum TreeType { RANDOM, PATH, STAR, DEEP, BINARY };
// parent[i] < i for i in [1, n), before relabelling
vector<int> tree_shape(int n, TreeType type) {
    vector<int> par(n, -1);
    FOR(i, 1, n) switch (type) {
            case PATH: par[i] = i - 1; break;
            case STAR: par[i] = 0; break;
            case DEEP: par[i] = rand(max(0, i - 3), i - 1); break;
            case BINARY: par[i] = (i - 1) / 2; break;
            default: par[i] = rand(0, i - 1);
        }
    return par;
}
// edges of a random tree on vertices 1..n, randomly relabelled and shuffled
vector<pii> tree_random(int n, TreeType type = RANDOM) {
    vector<int> par = tree_shape(n, type), label = array_perm(n);
    vector<pii> edges;
    FOR(i, 1, n) {
        int u = label[i], v = label[par[i]];
        if (prob(1, 2)) swap(u, v);
        edges.push_back({u, v});
    }
    shuffle(all(edges), mt);
    return edges;
}
// "p_2 p_3 ... p_n" format with p_i < i (rooted at 1)
vector<int> tree_parents(int n, TreeType type = RANDOM) {
    vector<int> par = tree_shape(n, type), p;
    FOR(i, 1, n) p.push_back(par[i] + 1);
    return p;
}
// simple graph (no self-loops / multi-edges) with exactly m edges
vector<pii> graph_random(int n, int m, bool connected = false) {
    assert(m <= 1LL * n * (n - 1) / 2 && (!connected || m >= n - 1));
    set<pii> used;
    vector<pii> edges;
    auto add = [&](int u, int v) {
        if (u == v || used.count({min(u, v), max(u, v)})) return;
        used.insert({min(u, v), max(u, v)});
        edges.push_back({u, v});
    };
    if (connected)
        for (auto [u, v] : tree_random(n)) add(u, v);
    while ((int)edges.size() < m) add(rand(1, n), rand(1, n));
    shuffle(all(edges), mt);
    return edges;
}
void print_edges(const vector<pii>& edges) {
    for (auto [u, v] : edges) out(u, v);
}

// ---------------------------------------------------------------- main
// argv[1] = seed (passed by run.sh); extra args come from `./run.sh -- a b c` as argv[2..]
signed main(int argc, char** argv) {
    mt.seed(argc > 1 ? atoll(argv[1]) : random_device{}());
    // int MAXN = argc > 2 ? atoi(argv[2]) : 10;

    int t = 1;
    out(t);
    FOR(t) {
        int n = rand(1, 10);
        out(n);
        out(array_random(n, 1, 10));
    }
    return 0;
}
