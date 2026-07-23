# Facebook Infer diagnostic format drift

Session-derived reference for tests that compare CodeChecker parse/analyze output across Infer versions.

## Observed drift

Different CI platforms can install different Infer versions:

- Linux legacy installer used `infer-linux64-v1.1.0.tar.xz`.
- macOS GitHub runners needed direct release download because Homebrew no longer ships an `infer` formula.
- Current macOS release asset: `https://github.com/facebook/infer/releases/download/v1.3.0/infer-osx-arm64-v1.3.0.tar.xz`.

Output drift seen in `infer-dead-store` diagnostics:

```text
# Older format
The value written to `&b` is never used. [infer-dead-store]

# Newer format
The value written to &b (type int) is never used. [infer-dead-store]
```

## Recommended test handling

Normalize both actual and expected output before comparing:

```python
def normalize_quotes(s):
    s = s.replace("\u2018", "'").replace(
        "\u2019", "'").replace("\\'", "'")
    return s.replace('`', '')


def normalize_infer_type(s):
    return re.sub(r'\s*\(type\s+\w+(?:\s*\*)*\)', '', s)

actual = normalize_infer_type(normalize_quotes(actual))
expected = normalize_infer_type(normalize_quotes(expected))
```

Keep the normalizer narrow: strip only formatting artifacts that are known to vary by Infer version, not checker names, severity, file, line, column, or message semantics.

### Regex limitation

The regex `r'\s*\(type\s+\w+(?:\s*\*)*\)'` handles `int` and `int*` but
not multi-word types like `const char*` or `unsigned int`. If Infer starts
emitting compound types, broaden to:

```python
re.sub(r'\s*\(type\s+[^)]+\)', '', s)
```

## CI install note

If Homebrew lacks `infer`, install from GitHub releases with architecture detection:

```bash
INFER_VERSION=1.3.0
ARCH=$(uname -m)
curl -sSL "https://github.com/facebook/infer/releases/download/v${INFER_VERSION}/infer-osx-${ARCH}-v${INFER_VERSION}.tar.xz" \
  | sudo tar -C /opt -xJ
sudo ln -sf "/opt/infer-osx-${ARCH}-v${INFER_VERSION}/bin/infer" /usr/local/bin/infer
infer --version
```
