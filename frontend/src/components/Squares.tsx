import React, { useState, useEffect } from 'react';

interface SquareProps {
  size: number;
  x: number;
  y: number;
  color: string;
  delay: number;
  isDarkMode?: boolean;
}

const Square: React.FC<SquareProps> = ({ size, x, y, color, delay, isDarkMode = true }) => {
  const [opacity, setOpacity] = useState(0);

  useEffect(() => {
    const timeout = setTimeout(() => {
      setOpacity(isDarkMode ? 0.1 : 0.15);
    }, delay);

    return () => clearTimeout(timeout);
  }, [delay, isDarkMode]);

  return (
    <div
      className="absolute rounded-lg transition-opacity duration-1000"
      style={{
        width: `${size}px`,
        height: `${size}px`,
        left: `${x}px`,
        top: `${y}px`,
        backgroundColor: color,
        opacity,
      }}
    />
  );
};

interface SquaresProps {
  count?: number;
  minSize?: number;
  maxSize?: number;
  colors?: string[];
  className?: string;
  isDarkMode?: boolean;
}

const Squares: React.FC<SquaresProps> = ({
  count = 20,
  minSize = 30,
  maxSize = 100,
  colors = ['#6366F1', '#8B5CF6', '#EC4899', '#10B981'],
  className = '',
  isDarkMode = true,
}) => {
  const [squares, setSquares] = useState<Array<SquareProps>>([]);
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const updateSize = () => {
      const container = document.getElementById('squares-container');
      if (container) {
        setContainerSize({
          width: container.offsetWidth,
          height: container.offsetHeight,
        });
      }
    };

    updateSize();
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);

  useEffect(() => {
    if (containerSize.width === 0 || containerSize.height === 0) return;

    const newSquares = Array.from({ length: count }).map((_, i) => {
      const size = Math.random() * (maxSize - minSize) + minSize;
      return {
        size,
        x: Math.random() * (containerSize.width - size),
        y: Math.random() * (containerSize.height - size),
        color: colors[Math.floor(Math.random() * colors.length)],
        delay: i * 150,
        isDarkMode,
      };
    });

    setSquares(newSquares);
  }, [containerSize, count, minSize, maxSize, colors, isDarkMode]);

  return (
    <div
      id="squares-container"
      className={`w-full h-full absolute overflow-hidden pointer-events-none ${className}`}
    >
      {squares.map((square, index) => (
        <Square key={index} {...square} />
      ))}
    </div>
  );
};

export default Squares; 