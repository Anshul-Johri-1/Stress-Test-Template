#!/usr/bin/env python3
"""Parallel stress tester. Usage: ./run.sh [N] [options] [-- generator args]   (./run.sh -h for help)"""
from __future__ import annotations

import argparse
import hashlib
import math
import os
import random
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # the folder with run.sh and your .cpp files
BUILD = ROOT / ".build"  # compiled binaries, precompiled header (cache, safe to delete)
FAIL = ROOT / "fail"  # last failing test; removed again when a full run passes
ROLES = ("generator", "correct", "wrong", "checker")

TTY = sys.stdout.isatty()


def _style(code):
    return (lambda s: f"\033[{code}m{s}\033[0m") if TTY else (lambda s: str(s))


RED, GREEN, YELLOW, BLUE, CYAN, PURPLE, DIM, BOLD = map(_style, ("31", "32", "33", "34", "36", "35", "2", "1"))

STD = "-std=c++20"
FLAGS = {
    "release": [STD, "-O2", "-DONLINE_JUDGE"],
    "checker": [STD, "-O2"],
    # wrong.cpp rebuilt this way on failure: debug() enabled + STL bounds checks
    "debug": [STD, "-O1", "-g", "-D_GLIBCXX_DEBUG", "-D_GLIBCXX_DEBUG_PEDANTIC"],
}
# 256 MB stack like Codeforces, so deep recursion doesn't segfault locally
LINK = ["-Wl,-stack_size,0x10000000"] if sys.platform == "darwin" else []

SIGNAL_HINTS = {
    "SIGSEGV": "out-of-bounds / null pointer / stack overflow",
    "SIGBUS": "out-of-bounds / null pointer / stack overflow",
    "SIGABRT": "assert failed, abort(), or uncaught exception",
    "SIGFPE": "division by zero",
    "SIGKILL": "killed (out of memory?)",
}


def rel(path: Path) -> str:
    """Short path for messages: relative to where you ran ./run.sh, e.g. fail/input.txt."""
    path = Path(path).resolve()
    for base in (Path.cwd(), ROOT):
        try:
            return str(path.relative_to(base))
        except ValueError:
            pass
    return str(path)


def die(msg):
    print(RED(msg), file=sys.stderr)
    sys.exit(2)


# ---------------------------------------------------------------------------------------- building


def find_cxx():
    if os.environ.get("CXX"):
        return os.environ["CXX"]
    for v in range(20, 9, -1):
        if p := shutil.which(f"g++-{v}"):
            return p
    return shutil.which("g++") or "g++"


class Builder:
    def __init__(self):
        self.cxx = find_cxx()
        self._pch: dict[str, list[str]] = {}
        self._locks = {v: threading.Lock() for v in FLAGS}
        self._header = None
        self._header_lock = threading.Lock()

    def _stdcpp_header(self):
        with self._header_lock:
            if self._header is None:
                self._header = ""
                try:
                    p = subprocess.run([self.cxx, STD, "-x", "c++", "-M", "-"], input="#include <bits/stdc++.h>\n",
                                       capture_output=True, text=True, timeout=60)
                    for tok in p.stdout.replace("\\\n", " ").split():
                        if tok.endswith("bits/stdc++.h"):
                            self._header = tok
                            break
                except (OSError, subprocess.SubprocessError):
                    pass
            return self._header

    def pch_flags(self, variant):
        """Precompiled <bits/stdc++.h> per flag set: ~3x faster compiles. Built once, then cached."""
        with self._locks[variant]:
            if variant in self._pch:
                return self._pch[variant]
            self._pch[variant] = []
            header = self._stdcpp_header()
            if not header:
                return []
            key = hashlib.sha1("\0".join([self.cxx, header, *FLAGS[variant]]).encode()).hexdigest()[:12]
            d = BUILD / "pch" / key
            gch = d / "bits" / "stdc++.h.gch"
            if not gch.exists():
                (d / "bits").mkdir(parents=True, exist_ok=True)
                link = d / "bits" / "stdc++.h"
                if not link.is_symlink():
                    link.symlink_to(header)
                tmp = gch.with_suffix(".tmp")
                p = subprocess.run([self.cxx, *FLAGS[variant], "-x", "c++-header", header, "-o", str(tmp)],
                                   capture_output=True)
                if p.returncode != 0:
                    return []
                tmp.rename(gch)
            self._pch[variant] = [f"-I{d}"]
            return self._pch[variant]

    def compile(self, src: Path, name: str, variant: str):
        """Returns (exe, cached, error)."""
        flags = FLAGS[variant] + LINK
        if Path(self.cxx).name.startswith("g++-"):  # skip loading Homebrew's libstdc++.dylib on every run
            flags = flags + ["-static-libstdc++", "-static-libgcc"]
        exe, keyfile = BUILD / name, BUILD / f"{name}.key"
        key = hashlib.sha1(src.read_bytes() + "\0".join([self.cxx, *flags]).encode()).hexdigest()
        if exe.exists() and keyfile.exists() and keyfile.read_text() == key:
            return exe, True, None
        keyfile.unlink(missing_ok=True)
        cmd = [self.cxx, *flags, *self.pch_flags(variant), src.name, "-o", str(exe)]
        p = subprocess.run(cmd, capture_output=True, text=True, cwd=src.parent)
        if p.returncode != 0:
            return None, False, p.stderr
        keyfile.write_text(key)
        return exe, False, None


@dataclass
class Prog:
    role: str
    src: Path
    cmd: list | None = None

    @property
    def is_cpp(self):
        return self.src.suffix == ".cpp"


def find_source(role):
    """role.cpp or role.py — whichever you edited last (empty files ignored)."""
    cands = [p for p in (ROOT / f"{role}.cpp", ROOT / f"{role}.py") if p.exists() and p.stat().st_size > 0]
    return Prog(role, max(cands, key=lambda p: p.stat().st_mtime)) if cands else None


def build_all(progs: list[Prog], builder: Builder, pool: ThreadPoolExecutor):
    BUILD.mkdir(exist_ok=True)
    t0 = time.perf_counter()
    futs = {}
    for p in progs:
        if p.is_cpp:
            futs[p.role] = pool.submit(builder.compile, p.src, p.role, "checker" if p.role == "checker" else "release")
        else:
            p.cmd = [sys.executable, str(p.src)]
    failed, notes = False, []
    for p in progs:
        if p.role not in futs:
            notes.append(f"{p.src.name}")
            continue
        exe, cached, err = futs[p.role].result()
        if err is not None:
            failed = True
            print(RED(BOLD(f"✗ Compilation failed: {p.src.name}")))
            print(err.rstrip())
        else:
            p.cmd = [str(exe)]
            notes.append(f"{p.src.name}{DIM(' (cached)') if cached else ''}")
    if failed:
        sys.exit(2)
    print(DIM("Built ") + ", ".join(notes) + DIM(f"  [{time.perf_counter() - t0:.1f}s, {Path(builder.cxx).name}]"))


# ---------------------------------------------------------------------------------------- running


@dataclass
class Run:
    status: str  # OK / RE / TLE / INT
    out: bytes
    err: bytes
    time: float
    detail: str = ""


class _TimedPopen(subprocess.Popen):
    """Popen that reaps with wait4() to get the child's own CPU time (immune to load from parallel tests)."""
    cpu = None

    def _try_wait(self, wait_flags):
        try:
            pid, sts, ru = os.wait4(self.pid, wait_flags)
        except ChildProcessError:
            return self.pid, 0
        if pid == self.pid:
            self.cpu = ru.ru_utime + ru.ru_stime
        return pid, sts


def execute(cmd, inp: bytes | None, tl: float, args=()) -> Run:
    """Run with CPU-time limit tl (wall-clock backstop 1.5*tl+0.5s catches infinite loops / sleeps)."""
    t0 = time.perf_counter()
    wall = 1.5 * tl + 0.5
    with _TimedPopen([*cmd, *args], stdin=subprocess.DEVNULL if inp is None else subprocess.PIPE,
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=False) as p:
        try:
            out, err = p.communicate(inp, timeout=wall)
        except subprocess.TimeoutExpired:
            p.kill()
            out, err = p.communicate()
            return Run("TLE", out, err, wall, f"still running after {wall:g}s (limit {tl:g}s), killed")
    dt = p.cpu if p.cpu is not None else time.perf_counter() - t0
    rc = p.returncode
    if rc == 0 and dt > tl:
        return Run("TLE", out, err, dt, f"used {dt:.2f}s CPU time (limit {tl:g}s)")
    p.stdout, p.stderr = out, err
    if rc == 0:
        return Run("OK", p.stdout, p.stderr, dt)
    if rc in (-signal.SIGINT, 130):
        return Run("INT", p.stdout, p.stderr, dt)
    if rc < 0:
        try:
            name = signal.Signals(-rc).name
        except ValueError:
            name = f"signal {-rc}"
        detail = name + (f" — {SIGNAL_HINTS[name]}" if name in SIGNAL_HINTS else "")
    else:
        detail = f"exit code {rc}"
    return Run("RE", p.stdout, p.stderr, dt, detail)


@dataclass
class Failure:
    verdict: str  # WA RE TLE BRUTE GEN CHECKER INT
    test: int
    seed: int | None
    inp: bytes
    exp: bytes | None = None
    got: bytes | None = None
    msg: str = ""
    stderr: bytes = b""
    stderr_of: str = ""
    exp_line: int | None = None
    got_line: int | None = None


def _tok(b: bytes, limit=60):
    s = b.decode(errors="replace")
    return s if len(s) <= limit else s[:limit] + "…"


def _tokens(b: bytes):
    return [(tok, ln) for ln, line in enumerate(b.split(b"\n"), 1) for tok in line.split()]


def _tok_eq(a: bytes, b: bytes, eps, icase):
    if a == b or (icase and a.lower() == b.lower()):
        return True
    if eps is not None:
        try:
            x, y = float(a), float(b)
        except ValueError:
            return False
        if math.isfinite(x) and math.isfinite(y):
            return abs(x - y) <= eps * max(1.0, abs(x))
    return False


def compare(exp: bytes, got: bytes, eps, icase):
    """Whitespace-insensitive token comparison. Returns None if equal, else (msg, exp_line, got_line)."""
    if exp == got or (eps is None and not icase and exp.split() == got.split()):
        return None
    te, tg = _tokens(exp), _tokens(got)
    for i in range(min(len(te), len(tg))):
        if not _tok_eq(te[i][0], tg[i][0], eps, icase):
            (e, el), (g, gl) = te[i], tg[i]
            where = f"line {el}" if el == gl else f"expected line {el}, received line {gl}"
            return f"token #{i + 1} ({where}): expected {GREEN(_tok(e))}, received {RED(_tok(g))}", el, gl
    if len(tg) < len(te):
        e, el = te[len(tg)]
        return (f"received output ended early: {len(tg)} tokens instead of {len(te)} "
                f"(next expected {GREEN(_tok(e))} on line {el})"), el, None
    if len(tg) > len(te):
        g, gl = tg[len(te)]
        return (f"extra output: {len(tg)} tokens instead of {len(te)} "
                f"(first extra {RED(_tok(g))} on line {gl})"), None, gl
    return None


class Tester:
    def __init__(self, args, gen, correct, wrong, checker):
        self.a, self.gen, self.correct, self.wrong, self.checker = args, gen, correct, wrong, checker
        self.brute_tl = max(5.0, 5 * args.time)
        self.max_wrong = self.max_correct = 0.0
        self._local = threading.local()
        self.first = None  # (input, expected, received) of test 1, for the preview

    def _tmpdir(self):
        if not hasattr(self._local, "d"):
            (BUILD / "tmp").mkdir(parents=True, exist_ok=True)
            self._local.d = Path(tempfile.mkdtemp(dir=BUILD / "tmp"))
        return self._local.d

    def run_test(self, i, seed):
        g = execute(self.gen.cmd, None, self.brute_tl, [str(seed), *self.a.gen_args])
        if g.status != "OK":
            return Failure("INT" if g.status == "INT" else "GEN", i, seed, b"", got=g.out,
                           msg=f"{self.gen.src.name}: {g.status} {g.detail}", stderr=g.err, stderr_of=self.gen.src.name)
        return self.judge(g.out, i, seed)

    def judge(self, inp: bytes, i, seed):
        exp = b""
        if self.correct:
            e = execute(self.correct.cmd, inp, self.brute_tl)
            if e.status != "OK":
                return Failure("INT" if e.status == "INT" else "BRUTE", i, seed, inp, got=e.out,
                               msg=f"{self.correct.src.name}: {e.status} — {e.detail}", stderr=e.err,
                               stderr_of=self.correct.src.name)
            exp = e.out
            self.max_correct = max(self.max_correct, e.time)
        w = execute(self.wrong.cmd, inp, self.a.time)
        self.max_wrong = max(self.max_wrong, w.time)
        if w.status != "OK":
            return Failure(w.status, i, seed, inp, exp if self.correct else None, w.out,
                           f"{self.wrong.src.name}: {w.detail}", w.err, self.wrong.src.name)
        if i == 1:
            self.first = (inp, exp if self.correct else None, w.out)
        if self.checker:
            d = self._tmpdir()
            fi, fe, fg = d / "input.txt", d / "expected.txt", d / "received.txt"
            fi.write_bytes(inp), fe.write_bytes(exp), fg.write_bytes(w.out)
            c = execute(self.checker.cmd, None, self.brute_tl, [str(fi), str(fe), str(fg)])
            if c.status == "OK":
                return None
            report = (c.out + c.err).decode(errors="replace").strip()
            if c.status == "RE" and c.detail.startswith("exit code"):
                return Failure("WA", i, seed, inp, exp if self.correct else None, w.out, report or c.detail)
            return Failure("INT" if c.status == "INT" else "CHECKER", i, seed, inp, exp, w.out,
                           f"{self.checker.src.name}: {c.status} — {c.detail}\n{report}".strip())
        if not self.correct:
            return None
        diff = compare(exp, w.out, self.a.eps, self.a.icase)
        if diff is None:
            return None
        return Failure("WA", i, seed, inp, exp, w.out, diff[0], w.err, self.wrong.src.name, diff[1], diff[2])


# ---------------------------------------------------------------------------------------- reporting


def block(title, data: bytes, file=None, hl=None, color=None, max_lines=40, numbered=False):
    text = data.decode(errors="replace")
    lines = text.splitlines()
    meta = ", ".join(x for x in [file, f"{len(lines)} line{'s' * (len(lines) != 1)}"] if x)
    print(BOLD(f"── {title} ") + DIM(f"({meta})"))
    if not lines:
        print(DIM("   <empty>"))
        return
    lo, hi = 0, len(lines)
    if len(lines) > max_lines:
        center = (hl - 1) if hl else 0
        lo = max(0, min(center - max_lines // 2, len(lines) - max_lines))
        hi = lo + max_lines
    if lo > 0:
        print(DIM(f"   … {lo} lines above"))
    w = len(str(hi))
    for idx in range(lo, hi):
        line = lines[idx]
        if len(line) > 300:
            line = line[:300] + DIM(f" … (+{len(line) - 300} chars)")
        gutter = DIM(f"{idx + 1:>{w}}│ ") if numbered else "   "
        if hl == idx + 1:
            print(gutter + (color or RED)(BOLD(line)) + DIM("  ◀"))
        else:
            print(gutter + line)
    if hi < len(lines):
        print(DIM(f"   … {len(lines) - hi} more lines" + (f" in {file}" if file else "")))


TITLES = {
    "WA": "Wrong Answer",
    "RE": "Runtime Error",
    "TLE": "Time Limit Exceeded",
    "BRUTE": "correct solution failed (bug in brute force?)",
    "GEN": "generator failed",
    "CHECKER": "checker crashed",
}


def report(f: Failure, tester: Tester, debug_build):
    where = f"test #{f.test}" + (f", seed {f.seed}" if f.seed is not None else "")
    print("\n" + RED(BOLD(f"✗ {TITLES[f.verdict]}")) + f" on {where}\n")
    shutil.rmtree(FAIL, ignore_errors=True)
    FAIL.mkdir()
    (FAIL / "input.txt").write_bytes(f.inp)
    if f.exp is not None:
        (FAIL / "expected.txt").write_bytes(f.exp)
    if f.got is not None:
        (FAIL / "received.txt").write_bytes(f.got)
    (FAIL / "verdict.txt").write_text(f.msg + "\n")

    if f.verdict != "GEN":
        block("Input", f.inp, "fail/input.txt", max_lines=50)
    if f.exp is not None:
        block("Expected", f.exp, "fail/expected.txt", f.exp_line, GREEN, numbered=True)
    if f.got is not None:
        block("Received" if f.verdict != "GEN" else "Generator output", f.got,
              "fail/received.txt" if f.verdict != "GEN" else None, f.got_line, RED, numbered=True)
    print(BOLD("── Verdict"))
    print("   " + f.msg.replace("\n", "\n   "))
    if f.stderr.strip():
        block(f"stderr of {f.stderr_of}", f.stderr, max_lines=25)

    # Re-run wrong.cpp built without ONLINE_JUDGE + with _GLIBCXX_DEBUG: shows debug() output and
    # catches out-of-bounds accesses that silently gave a wrong answer in the -O2 build.
    if debug_build and f.verdict in ("WA", "RE", "TLE"):
        exe, _, err = debug_build.result()
        if exe:
            r = execute([str(exe)], f.inp, max(10.0, 10 * tester.a.time))
            if r.err.strip():
                (FAIL / "debug.txt").write_bytes(r.err)
            notes = []
            if r.status == "RE":
                notes.append(YELLOW(f"debug build crashed: {r.detail}"))
            elif r.status == "OK" and f.got is not None and r.out.split() != f.got.split():
                notes.append(YELLOW("debug build printed a DIFFERENT answer → likely undefined behaviour "
                                    "(uninitialised variable, out-of-bounds, overflow)"))
            if r.err.strip() or notes:
                print(BOLD("── Debug run ") + DIM(f"({tester.wrong.src.name} without ONLINE_JUDGE, with _GLIBCXX_DEBUG)"))
                for n in notes:
                    print("   " + n)
                if r.err.strip():
                    block("debug() / stderr", r.err, "fail/debug.txt", max_lines=40)

    print()
    if f.seed is not None:
        print(DIM("Reproduce: ") + f"./run.sh -s {f.seed} 1" + DIM("   ·   re-run this test after a fix: ") + "./run.sh -f")
    else:
        print(DIM("Re-run after a fix: ") + "./run.sh -f")


def preview(inp, exp, got):
    print(CYAN(BOLD("First test")) + DIM(" (-q to hide)"))
    for title, data, n in (("input", inp, 8), ("expected", exp, 4), ("received", got, 4)):
        if data is None:
            continue
        lines = data.decode(errors="replace").splitlines()
        shown = [ln[:120] + ("…" if len(ln) > 120 else "") for ln in lines[:n]]
        more = DIM(f" … +{len(lines) - n} lines") if len(lines) > n else ""
        body = ("\n" + " " * 11).join(shown) if shown else DIM("<empty>")
        print(DIM(f"  {title:>8}: ") + body + more)


# ---------------------------------------------------------------------------------------- commands


def parse_args():
    argv = sys.argv[1:]
    gen_args = []
    if "--" in argv:
        k = argv.index("--")
        argv, gen_args = argv[:k], argv[k + 1:]
    ap = argparse.ArgumentParser(
        prog="./run.sh", formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Stress test wrong.{cpp,py} against correct.{cpp,py} on inputs from generator.{cpp,py}.",
        epilog="examples:\n"
               "  ./run.sh                 5000 tests, stop at first failure\n"
               "  ./run.sh 200 -t 1        200 tests, 1s time limit\n"
               "  ./run.sh -e 1e-6         compare floats with 1e-6 abs/rel tolerance\n"
               "  ./run.sh -c              judge with checker.cpp (multiple valid answers)\n"
               "  ./run.sh -m 500          after a failure, try 500 more tests for a smaller one\n"
               "  ./run.sh -f              re-run the last failing test (fail/input.txt)\n"
               "  ./run.sh -f my.txt       run once on any input file\n"
               "  ./run.sh -- 100 5        pass '100 5' to the generator as argv[2], argv[3]\n"
               "\nnext problem: git restore .   (blank templates are committed)\n"
               "without correct.cpp/.py, wrong is only checked for crashes / TLE (and by -c checker).")
    ap.add_argument("count", nargs="?", type=int, help="number of tests (default 5000)")
    ap.add_argument("-n", type=int, dest="n", default=5000, help=argparse.SUPPRESS)
    ap.add_argument("-t", "--time", type=float, default=2.0, metavar="SEC", help="time limit for wrong (default 2)")
    ap.add_argument("-j", "--jobs", type=int, default=os.cpu_count() or 4, help="parallel workers (default: #cpus)")
    ap.add_argument("-s", "--seed", type=int, help="seed of the first test (test k uses seed+k-1)")
    ap.add_argument("-c", "--checker", action="store_true", help="judge with checker.cpp instead of token diff")
    ap.add_argument("-e", "--eps", type=float, help="float tolerance (abs or relative)")
    ap.add_argument("-i", "--icase", action="store_true", help="case-insensitive tokens (YES == yes)")
    ap.add_argument("-m", "--minimize", type=int, default=0, metavar="K",
                    help="after the first failure run K more tests and report the smallest failing input")
    ap.add_argument("-f", "--file", type=Path, nargs="?", const=FAIL / "input.txt",
                    help="run once on this input file (default: fail/input.txt)")
    ap.add_argument("-q", "--quiet", action="store_true", help="don't preview the first test")
    a = ap.parse_args(argv)
    a.n = a.count if a.count is not None else a.n
    a.gen_args = gen_args
    return a


def main():
    a = parse_args()
    gen = None if a.file else find_source("generator")
    correct, wrong = find_source("correct"), find_source("wrong")
    checker = find_source("checker") if a.checker else None
    if a.file and not a.file.exists():
        die("No failing test saved yet. Run ./run.sh first." if a.file == FAIL / "input.txt" else f"{a.file} not found")
    if not wrong:
        die("wrong.cpp / wrong.py is missing or empty")
    if not a.file and not gen:
        die("generator.cpp / generator.py is missing or empty  (git restore generator.cpp)")
    if a.checker and not checker:
        die("-c given but checker.cpp is missing or empty  (git restore checker.cpp)")
    if correct and correct.src.read_bytes() == wrong.src.read_bytes():
        print(YELLOW(f"⚠ {correct.src.name} and {wrong.src.name} are identical"))
    if not correct:
        print(YELLOW("⚠ no correct.cpp/.py — only checking wrong for crashes / TLE" + (" + checker" if checker else "")))

    progs = [p for p in (gen, correct, wrong, checker) if p]
    builder = Builder()
    pool = ThreadPoolExecutor(max(4, a.jobs))
    # debug build of wrong.cpp compiles in the background; only needed if something fails
    debug_build = pool.submit(builder.compile, wrong.src, "wrong-debug", "debug") if wrong.is_cpp else None
    build_all(progs, builder, pool)
    t = Tester(a, gen, correct, wrong, checker)
    code = 0
    try:
        if a.file:
            code = run_file(a, t, debug_build)
        else:
            code = stress(a, t, debug_build, pool)
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
        shutil.rmtree(BUILD / "tmp", ignore_errors=True)
    sys.exit(code)


def run_file(a, t: Tester, debug_build):
    inp = a.file.read_bytes()
    f = t.judge(inp, 1, None)
    if f is None:
        print(GREEN(BOLD("✓ Passed")) + f" on {rel(a.file)}" + DIM(f"  (wrong {t.max_wrong:.3f}s)"))
        return 0
    report(f, t, debug_build)
    return 1


def stress(a, t: Tester, debug_build, pool):
    base = a.seed if a.seed is not None else random.randrange(1, 10**9)
    n, jobs = a.n, max(1, a.jobs)
    t0 = time.perf_counter()

    # test 1 runs on its own so the preview / sanity warnings show before the flood
    first = t.run_test(1, base)
    if t.first and (first is None or first.verdict == "WA"):
        inp, exp, got = t.first
        if not a.quiet and first is None:
            preview(inp, exp, got)
        if exp is not None and not exp.strip():
            print(YELLOW("⚠ correct printed nothing — forgot to paste the brute force?"))
        elif not got.strip():
            print(YELLOW("⚠ wrong printed nothing"))
    if first is not None and first.verdict == "INT":
        return 130

    fails = [first] if first else []
    done, next_i, inflight = 1, 2, set()
    stop_at = (1 + a.minimize) if first else None
    last_draw, interrupted = 0.0, False

    def draw(final=False):
        nonlocal last_draw
        now = time.perf_counter()
        if not TTY or (not final and now - last_draw < 0.1):
            return
        last_draw = now
        rate = done / max(now - t0, 1e-9)
        status = RED(f"{len(fails)} failing") if fails else GREEN(f"{done}/{n}")
        extra = f" · searching for a smaller failing test" if fails and stop_at and done < stop_at else ""
        times = f"max time: wrong {t.max_wrong:.3f}s" + (f", correct {t.max_correct:.3f}s" if t.correct else "")
        sys.stdout.write(f"\r\033[K  {status} {DIM(f'· {rate:.0f} tests/s · {times}{extra}')}")
        sys.stdout.flush()

    try:
        while True:
            limit = n if stop_at is None else min(n, stop_at)
            while len(inflight) < 2 * jobs and next_i <= limit and not interrupted:
                inflight.add(pool.submit(t.run_test, next_i, base + next_i - 1))
                next_i += 1
            if not inflight:
                break
            finished, inflight = wait(inflight, timeout=0.1, return_when=FIRST_COMPLETED)
            for fut in finished:
                f = fut.result()
                done += 1
                if f is not None:
                    if f.verdict == "INT":
                        raise KeyboardInterrupt
                    fails.append(f)
                    if stop_at is None:
                        stop_at = done + a.minimize
            draw()
    except KeyboardInterrupt:
        interrupted = True
        for fut in inflight:
            fut.cancel()
    draw(final=True)
    if TTY:
        print()
    elapsed = time.perf_counter() - t0

    if interrupted and not fails:
        print(YELLOW(f"Stopped after {done} tests") + DIM(f" ({elapsed:.1f}s), all passed"))
        return 130
    if not fails:
        shutil.rmtree(FAIL, ignore_errors=True)  # an old failure is no longer relevant
        print(GREEN(BOLD(f"✓ All {done} tests passed")) + DIM(f" in {elapsed:.1f}s  (seed {base})"))
        return 0
    # harness problems first (gen / brute / checker), then the smallest input
    f = min(fails, key=lambda x: (x.verdict in ("WA", "RE", "TLE"), len(x.inp), x.test))
    if len(fails) > 1:
        print(DIM(f"{len(fails)} failing tests found; showing the smallest"))
    report(f, t, debug_build)
    return 1


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(YELLOW("\ninterrupted"))
        sys.exit(130)
