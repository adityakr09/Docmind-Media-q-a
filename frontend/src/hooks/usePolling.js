import { useEffect, useRef } from "react";

/**
 * Polls a callback at a given interval while a condition is true.
 * Automatically clears on unmount.
 */
export default function usePolling(callback, intervalMs, active) {
  const savedCallback = useRef(callback);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!active) return;
    const tick = () => savedCallback.current();
    tick(); // immediate first call
    const id = setInterval(tick, intervalMs);
    return () => clearInterval(id);
  }, [intervalMs, active]);
}
