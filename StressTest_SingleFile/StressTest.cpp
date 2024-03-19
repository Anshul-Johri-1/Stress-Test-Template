#include <bits/stdc++.h>
using namespace std;

void generateTestCase();
namespace correct
{
    void brute();
}
void solve();

stringstream testCase, bruteCin, bruteCout, solveCin, solveCout;
string checker_log{"Outputs Don't Match"};

bool testCaseFailed()
{
    // cin.rdbuf(testCase.rdbuf());
    // cin.rdbuf(solveCout.rdbuf());
    string a, b;
    while (getline(bruteCout, a) and getline(solveCout, b))
    {
        while (a.back() == ' ')
            a.pop_back();
        while (b.back() == ' ')
            b.pop_back();
        if (a != b)
        {
            return true;
        }
    }
    return false;
}
void main2()
{
    int T = 1000;
    for (int t = 1; t <= T; t++)
    {
        // TestCase
        cout.rdbuf(testCase.rdbuf());
        generateTestCase();
        bruteCin << testCase.str();
        solveCin << testCase.str();
        if (t == 1)
            cerr << "Input Preview:" << endl
                 << testCase.str() << endl;

        // BruteForce
        cout.rdbuf(bruteCout.rdbuf());
        cin.rdbuf(bruteCin.rdbuf());
        correct::brute();

        // Solve
        cout.rdbuf(solveCout.rdbuf());
        cin.rdbuf(solveCin.rdbuf());
        solve();

        if (testCaseFailed())
        {
            cerr << "TestCase " << t << " Failed" << endl
                 << testCase.str() << endl
                 << "Expected Output :" << endl
                 << bruteCout.str() << endl
                 << "Received Output :" << endl
                 << solveCout.str() << endl
                 << "Checker_log" << endl
                 << checker_log << endl;
            return;
        }
        testCase = stringstream();
        bruteCout = stringstream();
        solveCout = stringstream();
    }
    cerr << T << " Testcases Passed" << endl;
}