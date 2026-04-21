import { expect, test } from "bun:test";

test("pytest suite", () => {
  const result = Bun.spawnSync(["poetry", "run", "pytest"], {
    stderr: "pipe",
    stdout: "pipe",
  });

  if (result.exitCode !== 0) {
    const stdout = new TextDecoder().decode(result.stdout);
    const stderr = new TextDecoder().decode(result.stderr);
    console.error(stdout);
    console.error(stderr);
  }

  expect(result.exitCode).toBe(0);
}, 300_000);
