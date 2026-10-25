import { describe, it, expect } from 'vitest';
import { analyzeComplexity, complexityGrowthData, normalizeGrowthClass } from './complexity-analysis';

describe('analyzeComplexity', () => {
  it('classifies constant time code', () => {
    const r = analyzeComplexity('x = 1 + 2\nprint(x)');
    expect(r.time.bigO).toBe('O(1)');
    expect(r.space.bigO).toBe('O(1)');
  });

  it('classifies a single loop as O(n)', () => {
    const r = analyzeComplexity('for i in range(n):\n    print(i)');
    expect(r.time.bigO).toBe('O(n)');
  });

  it('classifies nested loops as O(n^2)', () => {
    const r = analyzeComplexity('for i in range(n):\n    for j in range(n):\n        print(i, j)');
    expect(r.time.bigO).toBe('O(n^2)');
  });

  it('classifies binary search as O(log n)', () => {
    const code = 'while low <= high:\n    mid = (low + high) // 2\n    if a[mid] == x: break\n    elif a[mid] < x: low = mid + 1\n    else: high = mid - 1';
    const r = analyzeComplexity(code);
    expect(r.time.bigO).toBe('O(log n)');
  });

  it('detects recursion and reports stack space', () => {
    const code = 'def fact(n):\n    if n <= 1: return 1\n    return n * fact(n - 1)';
    const r = analyzeComplexity(code);
    expect(r.space.bigO).toBe('O(n)');
  });

  it('detects array growth as O(n) space', () => {
    const code = 'res = []\nfor i in range(n):\n    res.append(i)';
    const r = analyzeComplexity(code);
    expect(r.space.bigO).toBe('O(n)');
  });
});

describe('complexityGrowthData', () => {
  it('highlights the estimated class', () => {
    const data = complexityGrowthData('O(n)');
    expect(data.series.find((s) => s.highlight)?.label).toBe('O(n)');
  });

  it('normalizes quadratic estimates', () => {
    expect(normalizeGrowthClass('O(n^2)')).toBe('O(n^2)');
  });

  it('includes labeled growth series', () => {
    const data = complexityGrowthData('O(1)');
    expect(data.series.length).toBe(6);
    expect(data.series[0].values.length).toBe(5);
  });
});
