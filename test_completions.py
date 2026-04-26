import pexpect
import subprocess
import sys
import os

# Sentinel echoed between setup commands and the completion trigger so that
# unexpected-item checks only inspect completion output, not echoed paths.
_SENTINEL = 'COMP_SENTINEL_7f3a'


def test_shell(name, command, setup_commands, trigger_command,
               expected=None, unexpected=None):
    """Test shell completions via pexpect PTY interaction.

    Args:
        name: Test label for log output.
        command: Shell command to spawn.
        setup_commands: Lines sent before triggering completion.
        trigger_command: Text (including \\t) that triggers completion.
        expected: Ordered list of strings that must appear in output.
        unexpected: Strings that must NOT appear in the completion output.
    """
    print(f"Testing {name}...")

    if expected is None:
        expected = ['build', 'deploy', 'test']

    # Enforce a rich terminal environment for correct prompt/completion rendering
    env = os.environ.copy()
    env['TERM'] = 'xterm-256color'

    p = pexpect.spawn(command, env=env, encoding='utf-8')

    # Send setup configurations (e.g., sourcing files, binding tabs)
    for cmd in setup_commands:
        p.sendline(cmd)

    # When checking for unexpected items, place a sentinel after setup
    # commands to separate their echoed paths (which may coincidentally
    # contain completion words) from the actual completion output.
    if unexpected:
        p.sendline(f'echo {_SENTINEL}')
        try:
            p.expect(_SENTINEL, timeout=5)
        except pexpect.TIMEOUT:
            print(f"[{name}] TIMEOUT waiting for sentinel")
            sys.exit(1)

    # Trigger the completion via literal Tab key (\t)
    p.send(trigger_command)

    # Compgen, _describe, and fish all output completions alphabetically
    # So we assert against the ordered sequence in the output buffer
    collected_output = ''
    for item in expected:
        try:
            p.expect(item, timeout=5)
            collected_output += (p.before or '')
            if p.match:
                collected_output += p.match.group(0)
        except pexpect.TIMEOUT:
            print(f"[{name}] TIMEOUT waiting for '{item}'")
            print(f"Buffer dump: {p.buffer}")
            sys.exit(1)

    # When unexpected items are specified, verify they do not appear in the
    # completion output.  Wait briefly for any remaining terminal data, then
    # scan the accumulated output.
    if unexpected:
        p.expect([pexpect.TIMEOUT], timeout=1)
        collected_output += (p.before or '') + (p.buffer or '')

        for item in unexpected:
            if item in collected_output:
                print(f"[{name}] UNEXPECTED completion '{item}' found in output")
                print(f"Collected output: {collected_output!r}")
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

    print(f"[{name}] completion OK\n")


if __name__ == '__main__':
    cwd = os.getcwd()

    # --- Bash tests -----------------------------------------------------------

    bash_setup = [
        'bind "set show-all-if-ambiguous on"',
        f'source {cwd}/completions/mycli.bash',
    ]

    test_shell(
        name="Bash - all completions",
        command="bash --noprofile --norc",
        setup_commands=bash_setup,
        trigger_command='mycli \t',
    )

    test_shell(
        name="Bash - prefix 'de'",
        command="bash --noprofile --norc",
        setup_commands=bash_setup,
        trigger_command='mycli de\t',
        expected=['deploy'],
        unexpected=['build', 'test'],
    )

    test_shell(
        name="Bash - prefix 'bu'",
        command="bash --noprofile --norc",
        setup_commands=bash_setup,
        trigger_command='mycli bu\t',
        expected=['build'],
        unexpected=['deploy', 'test'],
    )

    # --- Zsh tests ------------------------------------------------------------

    zsh_setup = [
        'autoload -Uz compinit',
        f'fpath=({cwd}/completions $fpath)',
        'compinit -u',  # -u ignores insecure directory warnings in the sandbox
    ]

    test_shell(
        name="Zsh - all completions",
        command="zsh -f",
        setup_commands=zsh_setup,
        trigger_command='mycli \t',
        # Verify both subcommand names and their descriptions (zsh _describe feature)
        expected=['build', 'Build the project',
                  'deploy', 'Deploy the application',
                  'test', 'Run the test suite'],
    )

    test_shell(
        name="Zsh - prefix 'de'",
        command="zsh -f",
        setup_commands=zsh_setup,
        trigger_command='mycli de\t',
        expected=['deploy'],
        unexpected=['build', 'test'],
    )

    test_shell(
        name="Zsh - prefix 'bu'",
        command="zsh -f",
        setup_commands=zsh_setup,
        trigger_command='mycli bu\t',
        expected=['build'],
        unexpected=['deploy', 'test'],
    )

    # --- Fish tests -----------------------------------------------------------

    # Fish 4+ sends XTGETTCAP terminal capability queries on PTY startup, which
    # interferes with pexpect-based interactive testing.  Use `complete -C`
    # (Fish's built-in non-interactive completion query) instead.

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

    print("All PTY completion tests passed successfully.")
