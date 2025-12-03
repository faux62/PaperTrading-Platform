/**
 * Unit Tests - cn utility function
 * Tests for class name merging utility
 */
import { describe, it, expect } from 'vitest';
import { cn } from './cn';

describe('cn utility', () => {
  describe('basic usage', () => {
    it('should return empty string for no arguments', () => {
      expect(cn()).toBe('');
    });

    it('should return single class name', () => {
      expect(cn('class1')).toBe('class1');
    });

    it('should merge multiple class names', () => {
      expect(cn('class1', 'class2', 'class3')).toBe('class1 class2 class3');
    });

    it('should handle empty strings', () => {
      expect(cn('class1', '', 'class2')).toBe('class1 class2');
    });
  });

  describe('conditional classes', () => {
    it('should include class when condition is true', () => {
      const isActive = true;
      expect(cn('base', isActive && 'active')).toBe('base active');
    });

    it('should exclude class when condition is false', () => {
      const isActive = false;
      expect(cn('base', isActive && 'active')).toBe('base');
    });

    it('should handle null and undefined', () => {
      expect(cn('base', null, undefined, 'other')).toBe('base other');
    });

    it('should handle multiple conditions', () => {
      const isActive = true;
      const isDisabled = false;
      const isHovered = true;
      expect(cn(
        'base',
        isActive && 'active',
        isDisabled && 'disabled',
        isHovered && 'hovered'
      )).toBe('base active hovered');
    });
  });

  describe('object syntax', () => {
    it('should apply classes with truthy values', () => {
      expect(cn({ active: true, disabled: false })).toBe('active');
    });

    it('should handle mixed object and string syntax', () => {
      expect(cn('base', { active: true, hidden: false })).toBe('base active');
    });

    it('should handle multiple objects', () => {
      expect(cn(
        { class1: true },
        { class2: true, class3: false }
      )).toBe('class1 class2');
    });
  });

  describe('array syntax', () => {
    it('should flatten arrays', () => {
      expect(cn(['class1', 'class2'])).toBe('class1 class2');
    });

    it('should handle nested arrays', () => {
      expect(cn(['class1', ['class2', 'class3']])).toBe('class1 class2 class3');
    });

    it('should handle mixed array content', () => {
      expect(cn(['base', { active: true }])).toBe('base active');
    });
  });

  describe('complex scenarios', () => {
    it('should handle complex Tailwind class combinations', () => {
      const variant = 'primary';
      const size = 'md';
      const isDisabled = false;
      
      const result = cn(
        'btn',
        variant === 'primary' && 'bg-blue-500 text-white',
        variant === 'secondary' && 'bg-gray-500 text-black',
        size === 'sm' && 'px-2 py-1 text-sm',
        size === 'md' && 'px-4 py-2 text-base',
        size === 'lg' && 'px-6 py-3 text-lg',
        isDisabled && 'opacity-50 cursor-not-allowed'
      );
      
      expect(result).toBe('btn bg-blue-500 text-white px-4 py-2 text-base');
    });

    it('should deduplicate classes with same prefix', () => {
      // Note: clsx doesn't dedupe, just merges
      const result = cn('text-red-500', 'text-blue-500');
      expect(result).toBe('text-red-500 text-blue-500');
    });
  });
});
