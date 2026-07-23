"use client";

import { useRef, useState, useImperativeHandle, forwardRef, useEffect } from "react";
import type { Point } from "./canvasUtils";

export interface DrawingCanvasHandle {
  clear: () => void;
  getPoints: () => Point[];
  isEmpty: () => boolean;
}

interface DrawingCanvasProps {
  width?: number;
  height?: number;
}

const DrawingCanvas = forwardRef<DrawingCanvasHandle, DrawingCanvasProps>(
  ({ width = 800, height = 400 }, ref) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const pointsRef = useRef<Point[]>([]);
    const isDrawingRef = useRef(false);
    const [hasDrawing, setHasDrawing] = useState(false);

    const getCtx = () => canvasRef.current?.getContext("2d") ?? null;

    const clearCanvas = () => {
      const ctx = getCtx();
      const canvas = canvasRef.current;
      if (!ctx || !canvas) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      pointsRef.current = [];
      setHasDrawing(false);
    };

    useImperativeHandle(ref, () => ({
      clear: clearCanvas,
      getPoints: () => pointsRef.current,
      isEmpty: () => pointsRef.current.length === 0,
    }));

    const getRelativePos = (e: React.PointerEvent<HTMLCanvasElement>): Point => {
      const canvas = canvasRef.current!;
      const rect = canvas.getBoundingClientRect();
      return { x: e.clientX - rect.left, y: e.clientY - rect.top };
    };

    const handlePointerDown = (e: React.PointerEvent<HTMLCanvasElement>) => {
      isDrawingRef.current = true;
      const pos = getRelativePos(e);
      pointsRef.current = [pos];
      const ctx = getCtx();
      if (!ctx) return;
      ctx.beginPath();
      ctx.moveTo(pos.x, pos.y);
      setHasDrawing(true);
    };

    const handlePointerMove = (e: React.PointerEvent<HTMLCanvasElement>) => {
      if (!isDrawingRef.current) return;
      const pos = getRelativePos(e);
      pointsRef.current.push(pos);
      const ctx = getCtx();
      if (!ctx) return;
      ctx.lineTo(pos.x, pos.y);
      ctx.strokeStyle = "#22d3a8";
      ctx.lineWidth = 3;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.stroke();
    };

    const handlePointerUp = () => {
      isDrawingRef.current = false;
    };

    useEffect(() => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.fillStyle = "#12161f";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
    }, []);

    return (
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerLeave={handlePointerUp}
        className="rounded-lg border border-border touch-none cursor-crosshair"
      />
    );
  }
);

DrawingCanvas.displayName = "DrawingCanvas";

export default DrawingCanvas;