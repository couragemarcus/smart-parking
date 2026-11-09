import React, { useEffect } from 'react';

interface Props {
  message: string;
  variant?: 'success' | 'error' | 'info';
  onClose: () => void;
}

export const Toast: React.FC<Props> = ({ message, variant = 'info', onClose }) => {
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose();
    }, 3000);
    return () => clearTimeout(timer);
  }, [onClose]);

  const bgColor = {
    success: 'bg-green-600',
    error: 'bg-red-600',
    info: 'bg-blue-600'
  }[variant];

  return (
    <div className={`fixed bottom-4 right-4 ${bgColor} text-white px-6 py-3 rounded shadow-lg z-50 flex justify-between items-center animate-bounce`}>
      <span>{message}</span>
      <button onClick={onClose} className="ml-4 text-white hover:text-gray-200 font-bold">×</button>
    </div>
  );
};
