// Custom checker, used with `./run.sh -c` (problems with multiple valid answers, special output rules).
// Called as: checker <input> <expected> <received>
//   exit 0  -> accepted
//   exit 1  -> wrong answer (print the reason to stdout; it is shown in the report)
// debug(...) works here (not compiled with ONLINE_JUDGE).
#include <bits/stdc++.h>
using namespace std;

#include "Debug.cpp"

using ll = long long;
ifstream inf, ans, ouf;  // input, expected (from correct), received (from wrong)

template <typename... T>
[[noreturn]] void wa(const T&... msg) {
    ((cout << msg), ...) << endl;
    exit(1);
}
// read one token from the received output, failing cleanly if it is missing or malformed
template <typename T>
T read(const char* what = "value") {
    T x;
    if (!(ouf >> x)) wa("could not read ", what, " from received output");
    return x;
}
void expect_eof() {
    if (string extra; ouf >> extra) wa("extra output starting with '", extra, "'");
}

int main(int argc, char** argv) {
    if (argc < 4) wa("usage: checker <input> <expected> <received>");
    inf.open(argv[1]), ans.open(argv[2]), ouf.open(argv[3]);

    // ---- problem-specific checking goes here --------------------------------------
    // Typical "print -1 or any valid construction" pattern:
    //
    //   int t; inf >> t;
    //   for (int tc = 1; tc <= t; tc++) {
    //       int n; inf >> n; vector<ll> a(n); for (auto& x : a) inf >> x;
    //       ll best; ans >> best;                     // brute's answer (e.g. -1 / optimum)
    //       ll got = read<ll>("answer");
    //       if ((best == -1) != (got == -1)) wa("test ", tc, ": expected ", best, ", got ", got);
    //       if (got == -1) continue;
    //       vector<int> p(n); for (auto& x : p) x = read<int>("permutation");
    //       ... verify p is a valid construction for a, else wa("test ", tc, ": ...");
    //   }
    //   expect_eof();
    //
    // Default: plain token comparison, so `-c` works out of the box.
    for (int tok = 1;; tok++) {
        string e, r;
        bool he = bool(ans >> e), hr = bool(ouf >> r);
        if (!he && !hr) break;
        if (!hr) wa("received output ended early at token ", tok, ", expected '", e, "'");
        if (!he) wa("extra output at token ", tok, ": '", r, "'");
        if (e != r) wa("token ", tok, ": expected '", e, "', received '", r, "'");
    }
    return 0;
}
