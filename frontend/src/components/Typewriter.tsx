import { useState, useEffect } from 'react';

interface Props {
  text: string;
  speed?: number;
}

export const Typewriter = ({ text, speed = 30 }: Props) => {
  const [displayedText, setDisplayedText] = useState('');

  useEffect(() => {
    setDisplayedText('');
    let i = 0;
    const timer = setInterval(() => {
      if (i < text.length) {
        setDisplayedText((prev) => prev + text.charAt(i));
        i++;
      } else {
        clearInterval(timer);
      }
    }, speed);

    return () => clearInterval(timer);
  }, [text, speed]);

  return <>{displayedText}</>;
};
