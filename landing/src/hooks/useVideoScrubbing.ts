import { useEffect, useRef } from 'react';

export function useVideoScrubbing(videoRef: React.RefObject<HTMLVideoElement | null>) {
  const isSeekingRef = useRef(false);
  const targetTimeRef = useRef(0);
  const lastMouseXRef = useRef(0);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleSeeked = () => {
      isSeekingRef.current = false;
      // If there's a pending target time significantly different, update
      if (Math.abs(video.currentTime - targetTimeRef.current) > 0.05 && !isSeekingRef.current) {
        if (!isNaN(video.duration) && video.duration > 0) {
          isSeekingRef.current = true;
          video.currentTime = targetTimeRef.current;
        }
      }
    };

    video.addEventListener('seeked', handleSeeked);

    const handleMouseMove = (e: MouseEvent) => {
      if (!video || !video.duration || isNaN(video.duration)) return;

      const normX = e.clientX / window.innerWidth;
      const sensitivity = 0.8;
      
      // Calculate target time mapped across video duration
      let targetTime = normX * video.duration * sensitivity;
      targetTime = Math.max(0, Math.min(video.duration - 0.1, targetTime));
      
      targetTimeRef.current = targetTime;

      if (!isSeekingRef.current) {
        isSeekingRef.current = true;
        video.currentTime = targetTime;
      }
      lastMouseXRef.current = e.clientX;
    };

    window.addEventListener('mousemove', handleMouseMove);

    return () => {
      video.removeEventListener('seeked', handleSeeked);
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, [videoRef]);
}
