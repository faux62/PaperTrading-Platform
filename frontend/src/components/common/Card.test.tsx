/**
 * Unit Tests - Card Component
 * Tests for Card component and subcomponents
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import Card, { CardHeader, CardContent, CardFooter } from './Card';

describe('Card Component', () => {
  describe('rendering', () => {
    it('should render children', () => {
      render(<Card>Card content</Card>);
      expect(screen.getByText('Card content')).toBeInTheDocument();
    });

    it('should apply custom className', () => {
      const { container } = render(<Card className="custom-class">Content</Card>);
      expect(container.firstChild).toHaveClass('custom-class');
    });

    it('should render as a div element', () => {
      const { container } = render(<Card>Content</Card>);
      expect(container.querySelector('div')).toBeInTheDocument();
    });
  });

  describe('variants', () => {
    it('should apply default variant', () => {
      const { container } = render(<Card>Content</Card>);
      expect(container.firstChild).toHaveClass('bg-surface-800');
    });

    it('should apply elevated variant', () => {
      const { container } = render(<Card variant="elevated">Content</Card>);
      expect(container.firstChild).toHaveClass('shadow-lg');
    });

    it('should apply bordered variant', () => {
      const { container } = render(<Card variant="bordered">Content</Card>);
      expect(container.firstChild).toHaveClass('border');
    });
  });

  describe('padding', () => {
    it('should apply medium padding by default', () => {
      const { container } = render(<Card>Content</Card>);
      expect(container.firstChild).toHaveClass('p-4');
    });

    it('should apply small padding', () => {
      const { container } = render(<Card padding="sm">Content</Card>);
      expect(container.firstChild).toHaveClass('p-3');
    });

    it('should apply large padding', () => {
      const { container } = render(<Card padding="lg">Content</Card>);
      expect(container.firstChild).toHaveClass('p-6');
    });

    it('should apply no padding', () => {
      const { container } = render(<Card padding="none">Content</Card>);
      expect(container.firstChild).not.toHaveClass('p-3');
      expect(container.firstChild).not.toHaveClass('p-4');
      expect(container.firstChild).not.toHaveClass('p-6');
    });
  });

  describe('hover state', () => {
    it('should not have hover styles by default', () => {
      const { container } = render(<Card>Content</Card>);
      expect(container.firstChild).not.toHaveClass('cursor-pointer');
    });

    it('should apply hover styles when hover prop is true', () => {
      const { container } = render(<Card hover>Content</Card>);
      expect(container.firstChild).toHaveClass('cursor-pointer');
    });
  });

  describe('base styling', () => {
    it('should have rounded corners', () => {
      const { container } = render(<Card>Content</Card>);
      expect(container.firstChild).toHaveClass('rounded-xl');
    });
  });
});

describe('CardHeader Component', () => {
  it('should render title', () => {
    render(<CardHeader title="Test Title" />);
    expect(screen.getByText('Test Title')).toBeInTheDocument();
  });

  it('should render subtitle', () => {
    render(<CardHeader title="Title" subtitle="Subtitle" />);
    expect(screen.getByText('Subtitle')).toBeInTheDocument();
  });

  it('should render action element', () => {
    render(
      <CardHeader 
        title="Title" 
        action={<button>Action</button>} 
      />
    );
    expect(screen.getByRole('button')).toHaveTextContent('Action');
  });

  it('should render children', () => {
    render(<CardHeader>Custom Content</CardHeader>);
    expect(screen.getByText('Custom Content')).toBeInTheDocument();
  });
});

describe('CardContent Component', () => {
  it('should render children', () => {
    render(<CardContent>Main content</CardContent>);
    expect(screen.getByText('Main content')).toBeInTheDocument();
  });

  it('should apply custom className', () => {
    render(<CardContent className="custom-content">Content</CardContent>);
    expect(screen.getByText('Content')).toHaveClass('custom-content');
  });
});

describe('CardFooter Component', () => {
  it('should render children', () => {
    render(<CardFooter>Footer content</CardFooter>);
    expect(screen.getByText('Footer content')).toBeInTheDocument();
  });

  it('should apply custom className', () => {
    render(<CardFooter className="custom-footer">Footer</CardFooter>);
    expect(screen.getByText('Footer')).toHaveClass('custom-footer');
  });
});

describe('Card composition', () => {
  it('should compose Card with all subcomponents', () => {
    render(
      <Card>
        <CardHeader title="Card Title" subtitle="Card subtitle" />
        <CardContent>
          <p>This is the main content</p>
        </CardContent>
        <CardFooter>
          <button>Submit</button>
        </CardFooter>
      </Card>
    );

    expect(screen.getByText('Card Title')).toBeInTheDocument();
    expect(screen.getByText('Card subtitle')).toBeInTheDocument();
    expect(screen.getByText('This is the main content')).toBeInTheDocument();
    expect(screen.getByRole('button')).toHaveTextContent('Submit');
  });
});
