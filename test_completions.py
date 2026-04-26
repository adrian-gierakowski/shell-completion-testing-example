import pexpect
import subprocess
import sys
import os

def test_shell(name, command, setup_commands, trigger_command,
               expected=None):
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
        
    # Trigger the completion via literal Tab key (\t)
    p.send(trigger_command)
    
    # Compgen, _describe, and fish all output completions alphabetically
    # So we assert against the ordered sequence in the output buffer
    for item in expected:
        try:
            p.expect(item, timeout=5)
        except pexpect.TIMEOUT:
            print(f"[{name}] TIMEOUT waiting for '{item}'")
            print(f"Buffer dump: {p.buffer}")
            sys.exit(1)
            
    print(f"[{name}] completion OK\n")

if __name__ == '__main__':
    cwd = os.getcwd()
    
    test_shell(
        name="Bash",
        command="bash --noprofile --norc",
        setup_commands=[
            'bind "set show-all-if-ambiguous on"',
            f'source {cwd}/completions/mycli.bash',
        ],
        trigger_command='mycli \t'
    )

    test_shell(
        name="Zsh",
        command="zsh -f",
        setup_commands=[
            'autoload -Uz compinit',
            f'fpath=({cwd}/completions $fpath)',
            'compinit -u',  # -u ignores insecure directory warnings in the sandbox
        ],
        trigger_command='mycli \t',
        # Verify both subcommand names and their descriptions (zsh _describe feature)
        expected=['build', 'Build the project',
                  'deploy', 'Deploy the application',
                  'test', 'Run the test suite'],
    )

    # Fish 4+ sends XTGETTCAP terminal capability queries on PTY startup, which
    # interferes with pexpect-based interactive testing.  Use `complete -C`
    # (Fish's built-in non-interactive completion query) instead.
    print("Testing Fish...")
    fish_result = subprocess.run(
        ['fish', '-c', f'source {cwd}/completions/mycli.fish; complete -C "mycli "'],
        capture_output=True, text=True, timeout=10
    )
    fish_output = fish_result.stdout + fish_result.stderr
    for expected in ['build', 'deploy', 'test']:
        if expected not in fish_output:
            print(f"[Fish] MISSING '{expected}' in output")
            print(f"stdout: {fish_result.stdout!r}")
            print(f"stderr: {fish_result.stderr!r}")
            sys.exit(1)
    print("[Fish] completion OK\n")

    print("All PTY completion tests passed successfully.")
