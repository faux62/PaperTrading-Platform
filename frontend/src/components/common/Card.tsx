/**
 * Card Component
 */
import { HTMLAttributes, forwardRef } from 'react';
import { clsx } from 'clsx';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'elevated' | 'bordered';
  padding?: 'none' | 'sm' | 'md' | 'lg';
  hover?: boolean;
}

const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      className,
      variant = 'default',
      padding = 'md',
      hover = false,
      children,
      ...props
    },
    ref
  ) => {
    const variants = {
      default: 'bg-surface-800',
      elevated: 'bg-surface-800 shadow-lg shadow-black/20',
      bordered: 'bg-surface-800/50 border border-surface-700',
    };

    const paddings = {
      none: '',
      sm: 'p-3',
      md: 'p-4',
      lg: 'p-6',
    };

    return (
      <div
        ref={ref}
        className={clsx(
          'rounded-xl',
          variants[variant],
          paddings[padding],
          hover && 'transition-all duration-200 hover:bg-surface-700/80 cursor-pointer',
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

// Card Header subcomponent
interface CardHeaderProps extends HTMLAttributes<HTMLDivElement> {
  title?: string;
  subtitle?: string;
  action?: React.ReactNode;
}

export const CardHeader = forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ className, title, subtitle, action, children, ...props }, ref) => (
    <div
      ref={ref}
      className={clsx('flex items-center justify-between mb-4', className)}
      {...props}
    >
      <div>
        {title && <h3 className="text-lg font-semibold text-white">{title}</h3>}
        {subtitle && <p className="text-sm text-surface-400 mt-0.5">{subtitle}</p>}
        {children}
      </div>
      {action && <div>{action}</div>}
    </div>
  )
);

CardHeader.displayName = 'CardHeader';

// Card Title subcomponent
export const CardTitle = forwardRef<HTMLHeadingElement, HTMLAttributes<HTMLHeadingElement>>(
  ({ className, children, ...props }, ref) => (
    <h3
      ref={ref}
      className={clsx('text-lg font-semibold text-white', className)}
      {...props}
    >
      {children}
    </h3>
  )
);

CardTitle.displayName = 'CardTitle';

// Card Content subcomponent
export const CardContent = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => (
    <div ref={ref} className={clsx(className)} {...props}>
      {children}
    </div>
  )
);

CardContent.displayName = 'CardContent';

// Card Footer subcomponent
export const CardFooter = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => (
    <div
      ref={ref}
      className={clsx('mt-4 pt-4 border-t border-surface-700', className)}
      {...props}
    >
      {children}
    </div>
  )
);

CardFooter.displayName = 'CardFooter';

export default Card;
