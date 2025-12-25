"use client";

import { useEffect, useState } from "react";

interface LoadingProgressProps {
  isVisible: boolean;
}

export function LoadingProgress({ isVisible }: LoadingProgressProps) {
  const [progress, setProgress] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [isCompleting, setIsCompleting] = useState(false);

  useEffect(() => {
    if (!isVisible) {
      // Complete the progress bar before hiding
      if (progress > 0 && !isCompleting) {
        setIsCompleting(true);
        setProgress(100);
        setTimeout(() => {
          setProgress(0);
          setElapsedSeconds(0);
          setIsCompleting(false);
        }, 500);
      }
      return;
    }

    // Reset completion state when starting
    setIsCompleting(false);

    // Start progress animation
    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        // Slow down as it approaches 90% (never reaches 100% until done)
        if (prev < 90) {
          return prev + Math.random() * 2;
        }
        return Math.min(prev + 0.1, 95);
      });
    }, 200);

    // Track elapsed time
    const timeInterval = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);

    return () => {
      clearInterval(progressInterval);
      clearInterval(timeInterval);
    };
  }, [isVisible, progress, isCompleting]);

  // Show component while visible or completing
  if (!isVisible && !isCompleting) return null;

  const getStatusMessage = () => {
    if (isCompleting) {
      return "Almost done!";
    }
    if (elapsedSeconds < 5) {
      return "Fetching video transcript...";
    } else if (elapsedSeconds < 15) {
      return "Extracting recipe structure...";
    } else if (elapsedSeconds < 30) {
      return "This is taking a bit longer than usual...";
    } else if (elapsedSeconds < 60) {
      return "Still processing... This might take a while for longer videos.";
    } else {
      return "Hang tight! We're still working on extracting your recipe...";
    }
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 shadow-lg shadow-slate-950/40">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-slate-50">
            Extracting Recipe
          </h3>
          <span className="text-sm text-slate-400">
            {Math.round(progress)}%
          </span>
        </div>

        {/* Progress bar */}
        <div className="relative h-2 w-full overflow-hidden rounded-full bg-slate-800">
          <div
            className="h-full rounded-full bg-gradient-to-r from-primary via-primary-light to-primary transition-all duration-300 ease-out"
            style={{ width: `${progress}%` }}
          >
            <div className="h-full w-full animate-pulse bg-gradient-to-r from-transparent via-white/20 to-transparent" />
          </div>
        </div>

        {/* Status message */}
        <div className="flex items-center gap-2">
          <div className="h-2 w-2 animate-pulse rounded-full bg-primary" />
          <p className="text-sm text-slate-300">{getStatusMessage()}</p>
        </div>

        {/* Time indicator */}
        {elapsedSeconds > 10 && (
          <p className="text-xs text-slate-500">
            {elapsedSeconds > 60
              ? `Processing for ${Math.floor(elapsedSeconds / 60)}m ${elapsedSeconds % 60}s`
              : `Processing for ${elapsedSeconds}s`}
          </p>
        )}
      </div>
    </div>
  );
}

