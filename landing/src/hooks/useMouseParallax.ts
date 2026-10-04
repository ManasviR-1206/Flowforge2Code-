import { useState, useEffect } from 'react';

export function useMouseParallax() {
  const [parallax, setParallax] = useState({
    robotX: 0,
    robotY: 0,
    flowchartX: 0,
    flowchartY: 0,
    codeX: 0,
    codeY: 0,
  });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const { innerWidth, innerHeight } = window;
      if (innerWidth < 768) return; // Disable parallax on mobile

      const normX = (e.clientX - innerWidth / 2) / (innerWidth / 2);
      const normY = (e.clientY - innerHeight / 2) / (innerHeight / 2);

      setParallax({
        robotX: normX * 12,
        robotY: normY * 10,
        flowchartX: -normX * 18,
        flowchartY: -normY * 14,
        codeX: -normX * 22,
        codeY: -normY * 16,
      });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  return parallax;
}
