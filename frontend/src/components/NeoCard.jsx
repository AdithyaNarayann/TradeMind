const variants = {
  default: 'neo-card',
  teal: 'neo-card-teal',
  orange: 'neo-card-orange',
  maroon: 'neo-card-maroon',
  navy: 'neo-card-navy',
};

export default function NeoCard({ 
  children, 
  variant = 'default', 
  className = '',
  hover = false,
  ...props 
}) {
  return (
    <div 
      className={`
        ${variants[variant]}
        ${hover ? 'transition-all duration-150 hover:-translate-y-1 hover:shadow-neo-lg cursor-pointer' : ''}
        ${className}
      `}
      {...props}
    >
      {children}
    </div>
  );
}
