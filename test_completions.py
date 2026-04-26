import pexpect
import subprocess
import sys
import os


def _check_exact_set(name, actual, expected):
    """Compare *actual* candidate set against *expected* and exit on mismatch."""
    expected_set = set(expected)
    if actual != expected_set:
        print(f"[{name}] completion set mismatch")
        print(f"  expected: {sorted(expected_set)}")
        print(f"  actual:   {sorted(actual)}")
        if actual - expected_set:
            print(f"  unexpected: {sorted(actual - expected_set)}")
        if expected_set - actual:
            print(f"  missing: {sorted(expected_set - actual)}")
        sys.exit(1)


def test_bash(name, cwd, comp_words, expected):
    """Test Bash completions non-interactively via COMPREPLY inspection.

    Invokes the registered completion function with the given *comp_words*
    and compares the resulting COMPREPLY array against *expected* exactly.
    """
    print(f"Testing {name}...")

    words_bash = ' '.join(f'"{w}"' for w in comp_words)
    cword = len(comp_words) - 1

    bash_script = (
        f'source {cwd}/completions/mycli.bash\n'
        f'COMP_WORDS=({words_bash})\n'
        f'COMP_CWORD={cword}\n'
        f'_mycli\n'
        f'printf "%s\\n" "${{COMPREPLY[@]}}"\n'
    )

    result = subprocess.run(
        ['bash', '--noprofile', '--norc', '-c', bash_script],
        capture_output=True, text=True, timeout=10,
    )

    if result.returncode != 0:
        print(f"[{name}] command exited with status {result.returncode}")
        print(f"stderr: {result.stderr!r}")
        sys.exit(1)

    actual = {l.strip() for l in result.stdout.strip().splitlines() if l.strip()}
    _check_exact_set(name, actual, expected)
    print(f"[{name}] completion OK\n")


def test_zsh(name, cwd, comp_words, expected):
    """Test Zsh completions non-interactively via compadd capture.

    Loads the completion function through ``compinit`` + ``fpath`` (the
    standard Zsh mechanism), then overrides ``compadd`` to capture the
    candidates that ``_describe`` (or any other completion helper) passes
    to it.  The actual completion set is compared against *expected*
    exactly.

    This treats the completion script as a black box—only the public Zsh
    completion API (fpath, compinit, compadd) is used.
    """
    print(f"Testing {name}...")

    prefix = comp_words[-1]
    words_zsh = ' '.join(f'"{w}"' for w in comp_words)
    current = len(comp_words)

    zsh_script = f'''
autoload -Uz compinit
fpath=({cwd}/completions $fpath)
compinit -u

# --- Test harness: capture compadd candidates ---

typeset -a _captured
typeset _tags_iter=

# Override compadd to record completion candidates.
compadd() {{
  local -a _zo
  # Strip all standard compadd options; -D leaves positional args in $@.
  zparseopts -D -a _zo \\
    J: V: d: o: s: S: p: P: i: I: W: F: r: R: M+: x: X: E: \\
    q e f k l U Q n 1 2 C a O: A: D:

  # When -a is given, positional args are array names, not literals.
  local _has_a=0
  for _o in "${{_zo[@]}}"; do [[ "$_o" = "-a" ]] && _has_a=1; done

  local -a _cands
  if (( _has_a )); then
    for _n in "$@"; do _cands+=("${{(@P)_n}}"); done
  else
    _cands=("$@")
  fi

  # Apply the same PREFIX filtering that the real compadd would perform.
  for _c in "${{_cands[@]}}"; do
    if [[ -z "$PREFIX" || "$_c" == ${{PREFIX}}* ]]; then
      _captured+=("$_c")
    fi
  done
}}

# Stub _tags / _requested so _describe works outside a widget context.
# _tags must succeed on the first call and fail on the second to end
# the tag loop that _describe uses internally.
_tags() {{
  if [[ -n "$_tags_iter" ]]; then
    _tags_iter=
    return 1
  fi
  _tags_iter=1
  return 0
}}
_requested() {{ return 0; }}

# --- Set completion context and invoke the function ---

words=({words_zsh})
CURRENT={current}
PREFIX="{prefix}"

_mycli 2>/dev/null

printf '%s\\n' "${{_captured[@]}}"
'''

    result = subprocess.run(
        ['zsh', '-f', '-c', zsh_script],
        capture_output=True, text=True, timeout=10,
    )

    if result.returncode != 0:
        print(f"[{name}] command exited with status {result.returncode}")
        print(f"stderr: {result.stderr!r}")
        sys.exit(1)

    actual = {l.strip() for l in result.stdout.strip().splitlines() if l.strip()}
    _check_exact_set(name, actual, expected)
    print(f"[{name}] completion OK\n")


def test_zsh_interactive(name, command, setup_commands, trigger_command,
                         expected):
    """Verify Zsh interactive completion display (descriptions, formatting).

    Uses pexpect PTY interaction to check that expected strings appear in
    the completion output.  This complements ``test_zsh()`` by verifying
    the interactive user experience including description text rendered by
    ``_describe``.
    """
    print(f"Testing {name}...")

    env = os.environ.copy()
    env['TERM'] = 'xterm-256color'

    p = pexpect.spawn(command, env=env, encoding='utf-8')

    for cmd in setup_commands:
        p.sendline(cmd)

    p.send(trigger_command)

    for item in expected:
        try:
            p.expect(item, timeout=5)
        except pexpect.TIMEOUT:
            print(f"[{name}] TIMEOUT waiting for '{item}'")
            print(f"Buffer dump: {p.buffer}")
            sys.exit(1)

    print(f"[{name}] completion OK\n")


def test_fish(name, cwd, query, expected):
    """Test Fish completions using the non-interactive ``complete -C`` command.

    Validates that the command exits successfully and that the returned
    completion candidates match *expected* exactly.
    """
    print(f"Testing {name}...")

    fish_result = subprocess.run(
        ['fish', '-c',
         f'source {cwd}/completions/mycli.fish; complete -C "{query}"'],
        capture_output=True, text=True, timeout=10,
    )

    if fish_result.returncode != 0:
        print(f"[{name}] command exited with status {fish_result.returncode}")
        print(f"stderr: {fish_result.stderr!r}")
        sys.exit(1)

    # Parse completion candidates (first column before any tab-separated
    # description text).
    actual = set()
    for line in fish_result.stdout.strip().splitlines():
        candidate = line.split('\t')[0].strip()
        if candidate:
            actual.add(candidate)

    _check_exact_set(name, actual, expected)
    print(f"[{name}] completion OK\n")


if __name__ == '__main__':
    cwd = os.getcwd()

    # --- Bash tests -----------------------------------------------------------
    # Non-interactive: invoke _mycli directly and inspect COMPREPLY.

    test_bash(
        name="Bash - all completions",
        cwd=cwd,
        comp_words=['mycli', ''],
        expected=['build', 'deploy', 'test'],
    )

    test_bash(
        name="Bash - prefix 'de'",
        cwd=cwd,
        comp_words=['mycli', 'de'],
        expected=['deploy'],
    )

    test_bash(
        name="Bash - prefix 'bu'",
        cwd=cwd,
        comp_words=['mycli', 'bu'],
        expected=['build'],
    )

    # --- Zsh tests ------------------------------------------------------------
    # Non-interactive: load via compinit + fpath, capture compadd candidates.

    test_zsh(
        name="Zsh - all completions",
        cwd=cwd,
        comp_words=['mycli', ''],
        expected=['build', 'deploy', 'test'],
    )

    test_zsh(
        name="Zsh - prefix 'de'",
        cwd=cwd,
        comp_words=['mycli', 'de'],
        expected=['deploy'],
    )

    test_zsh(
        name="Zsh - prefix 'bu'",
        cwd=cwd,
        comp_words=['mycli', 'bu'],
        expected=['build'],
    )

    # Interactive PTY test: verify descriptions are displayed correctly.
    test_zsh_interactive(
        name="Zsh - descriptions",
        command="zsh -f",
        setup_commands=[
            'autoload -Uz compinit',
            f'fpath=({cwd}/completions $fpath)',
            'compinit -u',
        ],
        trigger_command='mycli \t',
        expected=['build', 'Build the project',
                  'deploy', 'Deploy the application',
                  'test', 'Run the test suite'],
    )

    # --- Fish tests -----------------------------------------------------------
    # Non-interactive: Fish's built-in ``complete -C`` query.
    # Fish 4+ sends XTGETTCAP terminal capability queries on PTY startup, which
    # interferes with pexpect-based interactive testing.

    test_fish(
        name="Fish - all completions",
        cwd=cwd,
        query="mycli ",
        expected=['build', 'deploy', 'test'],
    )

    test_fish(
        name="Fish - prefix 'de'",
        cwd=cwd,
        query="mycli de",
        expected=['deploy'],
    )

    test_fish(
        name="Fish - prefix 'bu'",
        cwd=cwd,
        query="mycli bu",
        expected=['build'],
    )

    print("All completion tests passed successfully.")
