export EDITOR='nvim'
export VISUAL='nvim'

time-cmd() {
  if [[ $# -eq 0 ]]; then
    echo "Usage: time-cmd <command and args...> or pipe a command line to it"
    return 1
  fi

  /usr/bin/time -lp "$@" 2>&1
}

format-cmd() {
  local flags_with_args=(-o -I -isystem -include -D -Xclang -analyzer-config -analyzer-checker -x --sysroot --target)
  local -A flag_map; for f in $flags_with_args; flag_map[$f]=1

  local args=()
  if [[ $# -gt 0 ]]; then
    args=("$@")
  else
    # Read from stdin, support multi-line and quoted args
    local input
    input="$(cat)"
    # Use zsh's array splitting to handle quoted arguments
    eval "args=($input)"
  fi

  local i=1
  while [[ $i -le ${#args[@]} ]]; do
    local arg="${args[$i]}"
    if [[ -n ${flag_map[$arg]} && $((i+1)) -le ${#args[@]} ]]; then
      printf "  %s %s" "$arg" "${args[$((i+1))]}"
      ((i+=2))
    else
      printf "  %s" "$arg"
      ((i++))
    fi
    if (( $i <= ${#args[@]} )); then
      printf " %s\n" "\\"
    fi
  done
  printf "\n"
}

function compile-cpp() {
  if [[ $# -eq 0 ]]; then
    echo "Usage: compile-cpp <source file> [<output file>] [<compiler flags>]"
    return 1
  fi

  local src="$1"
  local out="${2:-a.out}"
  shift 2 || shift # Remove first two args, or just the first if only one given

  clang++ \
    -std=c++20 \
    -march=native \
    -Wall \
    -Wextra \
    -Wshadow \
    -Wnon-virtual-dtor \
    -pedantic \
    -Wold-style-cast \
    -Wcast-align \
    -Wunused \
    -Woverloaded-virtual \
    -Wpedantic \
    -Wconversion \
    -Wsign-conversion \
    -Wmisleading-indentation \
    -Wnull-dereference \
    -Wdouble-promotion \
    -Wformat=2 \
    -Wimplicit-fallthrough \
    -Werror \
    -g \
    -fno-omit-frame-pointer \
    -O2 \
    "${src}" -o "${out}" "$@"
}

function compile-cpp-asan() {
  if [[ $# -eq 0 ]]; then
    echo "Usage: compile-cpp-asan <source file> [<output file>] [<compiler flags>]"
    return 1
  fi

  local src="$1"
  local out="${2:-a.out}"
  shift 2 || shift # Remove first two args, or just the first if only one given

  cpp "${src}" "${out}" -fsanitize=address,undefined "$@"
}
