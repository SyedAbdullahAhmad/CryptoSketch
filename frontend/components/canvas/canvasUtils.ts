export interface Point {
  x: number;
  y: number;
}

export function extractOrderedYValues(points: Point[], count: number = 60): number[] {
  if (points.length === 0) return [];

  const sorted = [...points].sort((a, b) => a.x - b.x);
  const xs = sorted.map((p) => p.x);
  const ys = sorted.map((p) => p.y);

  const minX = xs[0];
  const maxX = xs[xs.length - 1];
  if (maxX - minX === 0) return new Array(count).fill(ys[0]);

  const result: number[] = [];
  for (let i = 0; i < count; i++) {
    const targetX = minX + ((maxX - minX) * i) / (count - 1);
    result.push(interpolateY(xs, ys, targetX));
  }
  return result;
}

function interpolateY(xs: number[], ys: number[], targetX: number): number {
  if (targetX <= xs[0]) return ys[0];
  if (targetX >= xs[xs.length - 1]) return ys[ys.length - 1];

  for (let i = 0; i < xs.length - 1; i++) {
    if (targetX >= xs[i] && targetX <= xs[i + 1]) {
      const span = xs[i + 1] - xs[i];
      if (span === 0) return ys[i];
      const t = (targetX - xs[i]) / span;
      return ys[i] + t * (ys[i + 1] - ys[i]);
    }
  }
  return ys[ys.length - 1];
}