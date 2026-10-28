import { useRef, useState, type CSSProperties, type KeyboardEvent, type PointerEvent } from "react";

type SplitOptions = { storageKey: string; initial: number; axis: "x" | "y"; min: number; max: number };

const splitVars = (ratio: number) => ({ "--split-a": String(ratio), "--split-b": String(1 - ratio) });

export function useSplit({ storageKey, initial, axis, min, max }: SplitOptions) {
  const container = useRef<HTMLDivElement>(null);
  const [ratio, setRatio] = useState(() => {
    try {
      const stored = Number(localStorage.getItem(storageKey));
      return stored >= min && stored <= max ? stored : initial;
    } catch {
      return initial;
    }
  });
  const live = useRef(ratio);
  const [dragging, setDragging] = useState(false);

  const clamp = (value: number) => Math.min(max, Math.max(min, value));

  const paint = (value: number) => {
    live.current = value;
    for (const [name, css] of Object.entries(splitVars(value))) container.current?.style.setProperty(name, css);
  };

  const commit = (value: number) => {
    paint(value);
    setRatio(value);
    try {
      localStorage.setItem(storageKey, String(value));
    } catch {
      return;
    }
  };

  const fromPointer = (event: PointerEvent) => {
    const box = container.current?.getBoundingClientRect();
    if (!box) return live.current;
    return clamp(axis === "x" ? (event.clientX - box.left) / box.width : (event.clientY - box.top) / box.height);
  };

  const endDrag = () => {
    if (!dragging) return;
    setDragging(false);
    commit(live.current);
  };

  const handleProps = {
    role: "separator",
    tabIndex: 0,
    "aria-orientation": axis === "x" ? ("vertical" as const) : ("horizontal" as const),
    "aria-valuenow": Math.round(ratio * 100),
    "aria-valuemin": Math.round(min * 100),
    "aria-valuemax": Math.round(max * 100),
    "data-dragging": dragging ? "" : undefined,
    onPointerDown: (event: PointerEvent<HTMLElement>) => {
      event.currentTarget.setPointerCapture(event.pointerId);
      setDragging(true);
    },
    onPointerMove: (event: PointerEvent<HTMLElement>) => dragging && paint(fromPointer(event)),
    onPointerUp: endDrag,
    onPointerCancel: endDrag,
    onKeyDown: (event: KeyboardEvent) => {
      const back = axis === "x" ? "ArrowLeft" : "ArrowUp";
      const forward = axis === "x" ? "ArrowRight" : "ArrowDown";
      if (event.key === back) commit(clamp(ratio - 0.05));
      else if (event.key === forward) commit(clamp(ratio + 0.05));
      else return;
      event.preventDefault();
    },
  };

  return { container, style: splitVars(ratio) as CSSProperties, dragging, handleProps };
}
