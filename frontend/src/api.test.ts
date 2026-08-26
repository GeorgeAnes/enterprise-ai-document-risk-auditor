import { afterEach, describe, expect, it, vi } from "vitest";
import { COLD_START_MESSAGE, SLOW_REQUEST_THRESHOLD_MS, checkHealth, onSlowRequest } from "./api";

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

function mockFetchResolvingAfter(ms: number) {
  return vi.fn().mockImplementation(
    () =>
      new Promise((resolve) => {
        setTimeout(
          () =>
            resolve({
              ok: true,
              json: () => Promise.resolve({ status: "ok" })
            } as unknown as Response),
          ms
        );
      })
  );
}

describe("cold-start notice", () => {
  it("explains the scale-to-zero tradeoff rather than being a bare spinner", () => {
    // The message exists to teach a reviewer that the wait is a deliberate
    // choice. If it stops saying why, it has lost its whole purpose.
    expect(COLD_START_MESSAGE).toMatch(/scales to zero/i);
    expect(COLD_START_MESSAGE).toMatch(/€0\/month/);
  });

  it("does NOT fire for a fast request", async () => {
    vi.useFakeTimers();
    vi.stubGlobal("fetch", mockFetchResolvingAfter(10));

    const seen: boolean[] = [];
    const unsubscribe = onSlowRequest((slow) => seen.push(slow));

    const pending = checkHealth();
    await vi.advanceTimersByTimeAsync(20);
    await pending;
    unsubscribe();

    expect(seen).not.toContain(true);
  });

  it("fires once a request passes the threshold, then clears when it resolves", async () => {
    vi.useFakeTimers();
    vi.stubGlobal("fetch", mockFetchResolvingAfter(SLOW_REQUEST_THRESHOLD_MS + 500));

    const seen: boolean[] = [];
    const unsubscribe = onSlowRequest((slow) => seen.push(slow));

    const pending = checkHealth();
    await vi.advanceTimersByTimeAsync(SLOW_REQUEST_THRESHOLD_MS + 10);
    expect(seen).toContain(true);

    await vi.advanceTimersByTimeAsync(600);
    await pending;
    unsubscribe();

    expect(seen[seen.length - 1]).toBe(false);
  });

  it("clears the notice even when the request fails", async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(
        () =>
          new Promise((_resolve, reject) => {
            setTimeout(() => reject(new Error("network down")), SLOW_REQUEST_THRESHOLD_MS + 200);
          })
      )
    );

    const seen: boolean[] = [];
    const unsubscribe = onSlowRequest((slow) => seen.push(slow));

    const pending = checkHealth().catch(() => undefined);
    await vi.advanceTimersByTimeAsync(SLOW_REQUEST_THRESHOLD_MS + 300);
    await pending;
    unsubscribe();

    // A stuck "Waking the backend..." banner after a failure would be worse
    // than no banner at all.
    expect(seen[seen.length - 1]).toBe(false);
  });
});
