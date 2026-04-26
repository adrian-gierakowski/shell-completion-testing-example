# shell-completion-testing-example
Example of automated tests for shell completions

## Completions

The `mycli` command ships completion scripts for Bash, Zsh, and Fish.

### Zsh

Copy `completions/_mycli` to a directory in your `fpath` (e.g.
`/usr/local/share/zsh/site-functions/`) and run `compinit`:

```zsh
cp completions/_mycli /usr/local/share/zsh/site-functions/
autoload -Uz compinit && compinit
```

Zsh completions use `_describe` to show a short description next to each
subcommand when you press <kbd>Tab</kbd>:

```
$ mycli <Tab>
build   -- Build the project
deploy  -- Deploy the application
test    -- Run the test suite
```

## Testing

Completion tests use [pexpect](https://pexpect.readthedocs.io/) to drive real
interactive shell sessions over a PTY and assert that the expected completions
(including Zsh descriptions) appear in the output.

Run the tests via the Nix flake:

```sh
nix build
```
