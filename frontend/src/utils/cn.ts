/**
 * Class Name Utility
 * 
 * Wrapper for clsx to conditionally merge class names.
 * Common pattern in React + Tailwind CSS projects.
 */
import { clsx, type ClassValue } from 'clsx';

/**
 * Merge class names conditionally
 * @param inputs - Class values to merge (strings, objects, arrays)
 * @returns Merged class name string
 * 
 * @example
 * cn('base', condition && 'conditional', { active: isActive })
 * // => 'base conditional active' (if conditions are true)
 */
export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs);
}

export default cn;
