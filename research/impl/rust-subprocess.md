# Rust subprocess pattern

How to spawn Python, read its stdout, handle failures.

---

## the pipe deadlock problem

**Do not do this:**
```rust
let mut child = cmd.spawn()?;
let status = child.wait()?;              // blocks until Python exits
let mut out = String::new();
BufReader::new(child.stdout.take().unwrap()).read_to_string(&mut out)?;
```

If Python writes > ~4KB to stderr (traceback, warning flood), the stderr pipe fills, Python blocks
waiting for it to drain, `wait()` never returns. Deadlock.

**Correct approach: `Command::output()`:**
```rust
let output = Command::new("python")
    .args(&[...])
    .stdin(Stdio::null())
    .output()?;   // internally drains stdout + stderr concurrently, then waits
```

`output()` collects `stdout` and `stderr` as `Vec<u8>`, then returns `Output { status, stdout, stderr }`.
Safe for any output size.

---

## full pattern for this project

```rust
use std::process::{Command, Stdio};
use std::io;

pub fn run_python(args: &[&str]) -> Result<String, String> {
    let output = Command::new(python_exe())
        .args(args)
        .stdin(Stdio::null())
        .output()
        .map_err(|e| match e.kind() {
            io::ErrorKind::NotFound => format!(
                "Python not found in PATH. Install Python 3 and: pip install pymannkendall requests numpy scipy"
            ),
            _ => format!("failed to spawn Python: {e}"),
        })?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python exited with {}: {}", output.status, stderr.trim()));
    }

    String::from_utf8(output.stdout)
        .map_err(|e| format!("Python output was not valid UTF-8: {e}"))
}

fn python_exe() -> &'static str {
    // on Windows: "python" works if installed normally; "py" works if Python Launcher installed
    // try "python" first; on NotFound caller gets the helpful message and can retry with "py"
    "python"
}
```

---

## Python executable names on Windows

| command | when available |
|---|---|
| `python` | standard CPython install, added to PATH |
| `python3` | common on Linux/Mac, rarely on Windows |
| `py` | Windows Python Launcher (winpy.exe), always available if any Python is installed |

Strategy: try `python`, catch `NotFound`, retry with `py`, if still fails: print the install message.

```rust
fn spawn_python(args: &[&str]) -> Result<std::process::Output, String> {
    for exe in &["python", "py"] {
        match Command::new(exe).args(args).stdin(Stdio::null()).output() {
            Ok(out) => return Ok(out),
            Err(e) if e.kind() == io::ErrorKind::NotFound => continue,
            Err(e) => return Err(format!("spawn error: {e}")),
        }
    }
    Err("Python not found. Install Python 3 and: pip install pymannkendall requests numpy scipy".into())
}
```

---

## JSON parsing

Python outputs a single JSON object to stdout. Parse with serde_json:

```rust
let json_str = String::from_utf8(output.stdout)
    .map_err(|_| "non-UTF-8 output from Python".to_string())?;

let result: AnalysisResult = serde_json::from_str(&json_str)
    .map_err(|e| format!("could not parse Python output as JSON: {e}\nOutput was: {json_str}"))?;
```

Include the raw output in the parse error. When Python prints a warning before the JSON object
(e.g., a deprecation warning from numpy), serde_json will fail and the raw output tells you why.

To suppress Python warnings: pass `PYTHONWARNINGS=ignore` as an env var, or prefix Python invocation
with `python -W ignore analyze.py`.

---

## stderr forwarding

When Python fails (import error, API timeout, bad data), its traceback is in `output.stderr`.
Forward it cleanly:

```rust
if !output.status.success() {
    let stderr = String::from_utf8_lossy(&output.stderr);
    // strip blank lines, print indented
    for line in stderr.lines().filter(|l| !l.trim().is_empty()) {
        eprintln!("  {line}");
    }
    process::exit(1);
}
```

---

## what happens with each Python failure mode

| failure | spawn result | output.status | output.stderr |
|---|---|---|---|
| Python not in PATH | `Err(NotFound)` | n/a | n/a |
| import error (missing package) | `Ok(...)` | exit 1 | `ModuleNotFoundError: No module named 'pymannkendall'` |
| network timeout (NASA POWER API) | `Ok(...)` | exit 1 | timeout message |
| partial data / bad JSON from API | `Ok(...)` | exit 1 | Python traceback |
| success | `Ok(...)` | exit 0 | empty |
| numpy deprecation warning + valid JSON | `Ok(...)` | exit 0 | warning text, JSON in stdout |

The last row is the tricky one. Warnings on stderr are safe (stdout is clean JSON).
Warnings on stdout break serde_json parsing → always set `PYTHONWARNINGS=ignore`.
