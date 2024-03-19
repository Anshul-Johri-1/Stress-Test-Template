#include <bits/stdc++.h>
using namespace std;

signed main()
{
    ifstream expected_output("expected_output.txt");
    ifstream received_output("received_output.txt");
    for (string a, b; getline(expected_output, a) and getline(received_output, b);)
    {
        while (a.back() == ' ')
            a.pop_back();
        while (b.back() == ' ')
            b.pop_back();
        if (a != b)
        {
            cout << "Outputs Don't Match" << endl;
            return 1;
        }
    }
    // ifstream input("input.txt");
    // cin.rdbuf(input.rdbuf());
    // cin.rdbuf(expected_output.rdbuf());
    // cin.rdbuf(expected_output.rdbuf());
    // int t = 1;
    // cin >> t;
    // while (t--)
    // {
    // }

    return 0;
}