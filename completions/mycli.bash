_mycli() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local cmds="build test deploy"
    COMPREPLY=( $(compgen -W "${cmds}" -- "${cur}") )
    return 0
}
complete -F _mycli mycli
