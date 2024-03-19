#include <bits/stdc++.h>
using namespace std;

#define STRESS_TEST 1
#ifdef STRESS_TEST
#include "StressTest.cpp"
#endif

mt19937 mt(chrono::steady_clock::now().time_since_epoch().count());
int rand(int l, int r) { return l + mt() % (r - l + 1); }

void generateTestCase()
{
    // Write TestCase Generator
}
namespace correct
{
    void brute()
    {
        // BruteForce Solution Here
    }
}

void solve();
signed main()
{
#ifdef STRESS_TEST
    main2();
#else
    int T = 1;
    cin >> T;
    for (int t = 1; t <= T; t++)
    {
        solve();
    }
#endif
    return 0;
}
void solve()
{
    // Main Solution Here
}
