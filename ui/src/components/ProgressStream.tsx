"use client";

import { useEffect, useRef, useState } from "react";
import { apiBase } from "@/api";
import type { EvaluationResult } from "@/types";

interface ProgressStreamProps {
  jobId: string;
  onComplete: (results: EvaluationResult[]) => void;
  onError: (message: string) => void;
}

export default function ProgressStream({ jobId, onComplete, onError }: ProgressStreamProps) {
  const [done, setDone] = useState(0);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState<"connecting" | "streaming" | "complete" | "error">("connecting");
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const url = `${apiBase}/optimize/${jobId}/stream`;
    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onopen = () => {
      setStatus("streaming");
    };

    es.addEventListener("progress", (e) => {
      const data = JSON.parse(e.data);
      setDone(data.done);
      setTotal(data.total);
      setStatus("streaming");
    });

    es.addEventListener("complete", (e) => {
      const data = JSON.parse(e.data);
      setStatus("complete");
      es.close();
      onComplete(data.results);
    });

    es.addEventListener("error", (e) => {
      // SSE error event can be a MessageEvent (server-sent) or a generic Event (connection lost)
      if (e instanceof MessageEvent && e.data) {
        const data = JSON.parse(e.data);
        setStatus("error");
        es.close();
        onError(data.message || "Unknown error");
      } else {
        // Connection error - EventSource will auto-retry unless we close it
        // After 30s of no reconnect, give up
        setTimeout(() => {
          if (es.readyState === EventSource.CLOSED) {
            setStatus("error");
            onError("Connection lost");
          }
        }, 30000);
      }
    });

    return () => {
      es.close();
    };
  }, [jobId]); // eslint-disable-line react-hooks/exhaustive-deps

  const pct = total > 0 ? Math.round((done / total) * 100) : 0;

  return (
    <div className="space-y-3" role="progressbar" aria-valuenow={done} aria-valuemin={0} aria-valuemax={total}>
      <div className="flex items-center justify-between text-sm">
        <span className="text-zinc-600 dark:text-zinc-400">
          {status === "connecting" && "Connecting to worker..."}
          {status === "streaming" && `${done} / ${total} candidates evaluated`}
          {status === "complete" && "Optimization complete"}
          {status === "error" && "Error occurred"}
        </span>
        {total > 0 && (
          <span className="text-zinc-500 dark:text-zinc-500 font-mono text-xs">{pct}%</span>
        )}
      </div>
      <div className="w-full h-3 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden">
        <div
          className="h-full bg-amber-500 rounded-full transition-all duration-300 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
      {status === "connecting" && (
        <p className="text-xs text-zinc-500 dark:text-zinc-500 animate-pulse">
          Waiting for worker to start processing...
        </p>
      )}
    </div>
  );
}
