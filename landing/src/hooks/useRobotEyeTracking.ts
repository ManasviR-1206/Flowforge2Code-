import { useState, useEffect, useRef } from 'react';

export function useRobotEyeTracking(containerRef: React.RefObject<HTMLDivElement | null>) {
  const [pupilPos, setPupilPos] = useState({ x: 0, y: 0 });
  const [isBlinking, setIsBlinking] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  const targetPos = useRef({ x: 0, y: 0 });
  const currentPos = useRef({ x: 0, y: 0 });
  const animFrameId = useRef<number | null>(null);

  // Check mobile screen
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Blinking effect logic
  useEffect(() => {
    let blinkTimeout: ReturnType<typeof setTimeout>;

    const scheduleNextBlink = () => {
      const delay = Math.random() * 2500 + 2500; // 2.5s to 5s interval
      blinkTimeout = setTimeout(() => {
        setIsBlinking(true);
        setTimeout(() => {
          setIsBlinking(false);
          scheduleNextBlink();
        }, 160); // Eye shut duration 160ms
      }, delay);
    };

    scheduleNextBlink();
    return () => clearTimeout(blinkTimeout);
  }, []);

  // Eye tracking with smooth lerp interpolation
  useEffect(() => {
    if (isMobile) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;

      const rect = containerRef.current.getBoundingClientRect();
      const eyeCenterX = rect.left + rect.width / 2;
      const eyeCenterY = rect.top + rect.height / 2;

      const deltaX = e.clientX - eyeCenterX;
      const deltaY = e.clientY - eyeCenterY;

      const angle = Math.atan2(deltaY, deltaX);
      const distance = Math.hypot(deltaX, deltaY);

      // Max socket boundary offset radius in pixels
      const maxRadius = 14;
      const clampedDist = Math.min(distance * 0.08, maxRadius);

      targetPos.current = {
        x: Math.cos(angle) * clampedDist,
        y: Math.sin(angle) * clampedDist,
      };
    };

    const updateFrame = () => {
      // Lerp interpolation factor
      const lerp = 0.12;
      currentPos.current.x += (targetPos.current.x - currentPos.current.x) * lerp;
      currentPos.current.y += (targetPos.current.y - currentPos.current.y) * lerp;

      setPupilPos({
        x: currentPos.current.x,
        y: currentPos.current.y,
      });

      animFrameId.current = requestAnimationFrame(updateFrame);
    };

    window.addEventListener('mousemove', handleMouseMove);
    animFrameId.current = requestAnimationFrame(updateFrame);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      if (animFrameId.current) cancelAnimationFrame(animFrameId.current);
    };
  }, [containerRef, isMobile]);

  return { pupilPos, isBlinking, isMobile };
}
