/**
 * Unit Tests - Button Component
 * Tests for Button component variants, states, and interactions
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Button from './Button';

describe('Button Component', () => {
  describe('rendering', () => {
    it('should render children text', () => {
      render(<Button>Click me</Button>);
      expect(screen.getByRole('button')).toHaveTextContent('Click me');
    });

    it('should render as a button element', () => {
      render(<Button>Test</Button>);
      expect(screen.getByRole('button')).toBeInTheDocument();
    });

    it('should apply custom className', () => {
      render(<Button className="custom-class">Test</Button>);
      expect(screen.getByRole('button')).toHaveClass('custom-class');
    });
  });

  describe('variants', () => {
    it('should apply primary variant by default', () => {
      render(<Button>Primary</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-primary-600');
    });

    it('should apply secondary variant', () => {
      render(<Button variant="secondary">Secondary</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-surface-700');
    });

    it('should apply danger variant', () => {
      render(<Button variant="danger">Danger</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-danger-600');
    });

    it('should apply success variant', () => {
      render(<Button variant="success">Success</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-success-600');
    });

    it('should apply ghost variant', () => {
      render(<Button variant="ghost">Ghost</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-transparent');
    });

    it('should apply outline variant', () => {
      render(<Button variant="outline">Outline</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('border');
    });
  });

  describe('sizes', () => {
    it('should apply medium size by default', () => {
      render(<Button>Medium</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('px-4', 'py-2');
    });

    it('should apply small size', () => {
      render(<Button size="sm">Small</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('px-3', 'py-1.5');
    });

    it('should apply large size', () => {
      render(<Button size="lg">Large</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('px-6', 'py-3');
    });
  });

  describe('loading state', () => {
    it('should be disabled when loading', () => {
      render(<Button loading>Loading</Button>);
      expect(screen.getByRole('button')).toBeDisabled();
    });

    it('should show loader when loading', () => {
      render(<Button loading>Loading</Button>);
      const button = screen.getByRole('button');
      // Loader2 icon should be present
      const svg = button.querySelector('svg');
      expect(svg).toBeInTheDocument();
    });
  });

  describe('disabled state', () => {
    it('should be disabled when disabled prop is true', () => {
      render(<Button disabled>Disabled</Button>);
      expect(screen.getByRole('button')).toBeDisabled();
    });

    it('should apply disabled styles', () => {
      render(<Button disabled>Disabled</Button>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('disabled:opacity-50');
    });
  });

  describe('fullWidth prop', () => {
    it('should apply full width class', () => {
      render(<Button fullWidth>Full Width</Button>);
      expect(screen.getByRole('button')).toHaveClass('w-full');
    });

    it('should not apply full width by default', () => {
      render(<Button>Normal</Button>);
      expect(screen.getByRole('button')).not.toHaveClass('w-full');
    });
  });

  describe('icons', () => {
    it('should render left icon', () => {
      const Icon = () => <span data-testid="left-icon">←</span>;
      render(<Button leftIcon={<Icon />}>With Icon</Button>);
      expect(screen.getByTestId('left-icon')).toBeInTheDocument();
    });

    it('should render right icon', () => {
      const Icon = () => <span data-testid="right-icon">→</span>;
      render(<Button rightIcon={<Icon />}>With Icon</Button>);
      expect(screen.getByTestId('right-icon')).toBeInTheDocument();
    });

    it('should not render right icon when loading', () => {
      const Icon = () => <span data-testid="right-icon">→</span>;
      render(<Button loading rightIcon={<Icon />}>Loading</Button>);
      expect(screen.queryByTestId('right-icon')).not.toBeInTheDocument();
    });
  });

  describe('click handling', () => {
    it('should call onClick when clicked', () => {
      const handleClick = vi.fn();
      render(<Button onClick={handleClick}>Click me</Button>);
      
      fireEvent.click(screen.getByRole('button'));
      
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('should not call onClick when disabled', () => {
      const handleClick = vi.fn();
      render(<Button disabled onClick={handleClick}>Disabled</Button>);
      
      fireEvent.click(screen.getByRole('button'));
      
      expect(handleClick).not.toHaveBeenCalled();
    });

    it('should not call onClick when loading', () => {
      const handleClick = vi.fn();
      render(<Button loading onClick={handleClick}>Loading</Button>);
      
      fireEvent.click(screen.getByRole('button'));
      
      expect(handleClick).not.toHaveBeenCalled();
    });
  });

  describe('HTML attributes', () => {
    it('should forward type attribute', () => {
      render(<Button type="submit">Submit</Button>);
      expect(screen.getByRole('button')).toHaveAttribute('type', 'submit');
    });

    it('should forward data attributes', () => {
      render(<Button data-testid="custom-button">Test</Button>);
      expect(screen.getByTestId('custom-button')).toBeInTheDocument();
    });

    it('should forward aria attributes', () => {
      render(<Button aria-label="Custom label">Test</Button>);
      expect(screen.getByRole('button')).toHaveAttribute('aria-label', 'Custom label');
    });
  });

  describe('ref forwarding', () => {
    it('should forward ref to button element', () => {
      const ref = vi.fn();
      render(<Button ref={ref}>Test</Button>);
      expect(ref).toHaveBeenCalled();
    });
  });
});
