import { forwardRef } from 'react';

const variants = {
  default: 'neo-btn',
  teal: 'neo-btn-teal',
  orange: 'neo-btn-orange',
  maroon: 'neo-btn-maroon',
  navy: 'neo-btn-navy',
};

const sizes = {
  sm: 'px-4 py-2 text-sm',
  md: 'px-6 py-3 text-base',
  lg: 'px-8 py-4 text-lg',
};

const NeoButton = forwardRef(({ 
  children, 
  variant = 'default', 
  size = 'md',
  danger = false,
  className = '',
  ...props 
}, ref) => {
  return (
    <button 
      ref={ref}
      className={`
        ${variants[variant]}
        ${sizes[size]}
        ${danger ? 'neo-danger' : ''}
        ${className}
      `}
      {...props}
    >
      {children}
    </button>
  );
});

NeoButton.displayName = 'NeoButton';

export default NeoButton;
