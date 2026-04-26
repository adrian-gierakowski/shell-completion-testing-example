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
    """Test Zsh completions non-interactively by evaluating the candidate array.

    Loads the ``_mycli`` completion file in Zsh (stripping the ``#compdef``
    directive and the ``_describe`` call), which populates the ``cmds``
    array with ``key:description`` entries.  Candidates are then extracted,
    filtered by the current prefix, and compared against *expected* exactly.
    """
    print(f"Testing {name}...")

    prefix = comp_words[-1]
    comp_file = f'{cwd}/completions/_mycli'

    zsh_script = f'''
eval "$(sed '/#compdef/d; /_describe/d' {comp_file})"
prefix="{prefix}"
for entry in "${{cmds[@]}}"; do
  candidate="${{entry%%:*}}"
  if [[ -z "$prefix" || "$candidate" == ${{prefix}}* ]]; then
    print "$candidate"
  fi
done
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
    # Non-interactive: evaluate the candidate array from _mycli directly.

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
