/**
 * Badge Component
 */
import { HTMLAttributes, forwardRef } from 'react';
import { clsx } from 'clsx';

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'danger' | 'warning' | 'info' | 'outline';
  size?: 'sm' | 'md';
  dot?: boolean;
}

const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = 'default', size = 'md', dot = false, children, ...props }, ref) => {
    const variants = {
      default: 'bg-surface-700 text-surface-300',
      success: 'bg-success-500/20 text-success-400',
      danger: 'bg-danger-500/20 text-danger-400',
      warning: 'bg-warning-500/20 text-warning-400',
      info: 'bg-primary-500/20 text-primary-400',
      outline: 'bg-transparent border border-surface-600 text-surface-400',
    };

    const sizes = {
      sm: 'px-2 py-0.5 text-xs',
      md: 'px-2.5 py-1 text-xs',
    };

    const dotColors = {
      default: 'bg-surface-400',
      success: 'bg-success-400',
      danger: 'bg-danger-400',
      warning: 'bg-warning-400',
      info: 'bg-primary-400',
      outline: 'bg-surface-400',
    };

    return (
      <span
        ref={ref}
        className={clsx(
          'inline-flex items-center font-medium rounded-full',
          variants[variant],
          sizes[size],
          className
        )}
        {...props}
      >
        {dot && (
          <span
            className={clsx(
              'w-1.5 h-1.5 rounded-full mr-1.5',
              dotColors[variant]
            )}
          />
        )}
        {children}
      </span>
    );
  }
);

Badge.displayName = 'Badge';

export default Badge;
