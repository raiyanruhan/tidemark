mod cli;
mod locations;
mod output;

use std::process;

fn main() {
    if let Err(e) = cli::run() {
        eprintln!("error: {e}");
        process::exit(1);
    }
    process::exit(0);
}
