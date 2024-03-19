RESET='\033[0m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'   
PURPLE='\033[0;35m' 

set -e

g++ Generator.cpp -std=c++20 -DONLINE_JUDGE -o Generator.exe
g++ Correct.cpp -std=c++20 -DONLINE_JUDGE -o Correct.exe
g++ Wrong.cpp -std=c++20 -DONLINE_JUDGE -o Wrong.exe
g++ Checker.cpp -std=c++20 -DONLINE_JUDGE -o Checker.exe

NUM_TESTS=50

print_and_exit() {
    echo -e "\n${PURPLE}Wrong Answer on TestCase:${RESET}"
    cat input.txt
    echo -e "${BLUE}\nExpected Output:${RESET}"
    cat expected_output.txt
    echo -e "${RED}\nReceived Output:${RESET}"
    cat received_output.txt
    echo -e "${YELLOW}\nChecker Log:${RESET}"
    cat checker_log.txt
    rm *.exe
    rm *.txt
    exit 1
}

for ((i=1;i<=$NUM_TESTS;i++)); do
    ./Generator.exe > input.txt
    if [ "$i" -eq 1 ]; then
        echo -e "${CYAN}Input Preview"
        cat input.txt
        echo -e "${RESET}"
    fi
    
    ./Correct.exe < input.txt > expected_output.txt || print_and_exit
    
    ./Wrong.exe < input.txt > received_output.txt || print_and_exit
    
    ./Checker.exe > checker_log.txt || print_and_exit
    
    echo -e "${GREEN}TestCase $i Passed!${RESET}"
done

rm *.exe
rm *.txt

# cd StressTest_MultipleFile/ && chmod +x run.sh
# ./run.sh