/**
 * Lightweight structural complexity analysis for generated Python code.
 *
 * This is a heuristic, not a proof: it inspects loops, recursion, sorting and
 * common data-structure operations. Arbitrary programs cannot always be
 * classified exactly, so assumptions and uncertainty are reported alongside
 * the result.
 */

export interface ComplexityFinding {
  bigO: string;
  best: string;
  average: string;
  worst: string;
  explanation: string;
  influential: string[];
  assumptions: string[];
}

export interface SpaceComplexityFinding {
  bigO: string;
  explanation: string;
  influential: string[];
  assumptions: string[];
}

export interface ComplexityResult {
  time: ComplexityFinding;
  space: SpaceComplexityFinding;
}

function splitLines(code: string): string[] {
  return code.split(/\r?\n/);
}

function indentOf(line: string): number {
  const m = line.match(/^(\s*)/);
  return m ? m[1].replace(/\t/g, '    ').length : 0;
}

export type GrowthClass = 'O(1)' | 'O(log n)' | 'O(n)' | 'O(n log n)' | 'O(n^2)' | 'O(2^n)';

export function normalizeGrowthClass(bigO: string): GrowthClass {
  const s = (bigO || '').toLowerCase().replace(/\s+/g, ' ');
  if (s.includes('2^n') || s.includes('2n')) return 'O(2^n)';
  if (s.includes('n^2') || s.includes('n²')) return 'O(n^2)';
  if (s.includes('n log n')) return 'O(n log n)';
  if (s.includes('log n')) return 'O(log n)';
  if (s.includes('o(n)') || /^o\(n/.test(s)) return 'O(n)';
  return 'O(1)';
}

export function complexityGrowthData(estimate: string, points = [1, 2, 4, 8, 16]): {
  classes: GrowthClass[];
  series: { label: GrowthClass; values: number[]; highlight: boolean }[];
} {
  const highlight = normalizeGrowthClass(estimate);
  const classes: GrowthClass[] = ['O(1)', 'O(log n)', 'O(n)', 'O(n log n)', 'O(n^2)', 'O(2^n)'];
  const valueFor = (cls: GrowthClass, n: number): number => {
    switch (cls) {
      case 'O(1)': return 1;
      case 'O(log n)': return Math.log2(Math.max(n, 1));
      case 'O(n)': return n;
      case 'O(n log n)': return n * Math.log2(Math.max(n, 1));
      case 'O(n^2)': return n * n;
      case 'O(2^n)': return Math.pow(2, n);
      default: return n;
    }
  };
  const series = classes.map((cls) => ({
    label: cls,
    values: points.map((n) => valueFor(cls, n)),
    highlight: cls === highlight,
  }));
  return { classes, series };
}

export function analyzeComplexity(code: string): ComplexityResult {
  const lines = splitLines(code);
  const influential: string[] = [];
  const assumptions: string[] = [
    'Input size is denoted by n.',
    'Generated code is treated as the complete program; runtime/IO costs are ignored.',
    'Branches that depend on input distribution are classified by worst case unless noted.',
  ];

  // --- loop depth ---------------------------------------------------------
  let maxLoopDepth = 0;
  let currentDepth = 0;
  const loopStack: number[] = [];
  lines.forEach((raw, i) => {
    const line = raw.trim();
    if (!line || line.startsWith('#')) return;
    const ind = indentOf(raw);
    while (loopStack.length && ind <= loopStack[loopStack.length - 1]) {
      loopStack.pop();
      currentDepth = loopStack.length;
    }
    if (/^(for|while)\b/.test(line)) {
      currentDepth += 1;
      loopStack.push(ind);
      if (currentDepth > maxLoopDepth) maxLoopDepth = currentDepth;
      influential.push(`Line ${i + 1}: loop (${line.slice(0, 60)})`);
    }
  });

  // --- recursion ----------------------------------------------------------
  const funcDefs = new Set<string>();
  lines.forEach((l) => {
    const m = l.match(/^\s*def\s+([A-Za-z_]\w*)\s*\(/);
    if (m) funcDefs.add(m[1]);
  });
  const recursiveFns: string[] = [];
  funcDefs.forEach((fn) => {
    // A function is recursive if its name appears again after its def line.
    const defIndex = lines.findIndex((l) => new RegExp(`^\\s*def\\s+${fn}\\s*\\(`).test(l));
    const body = lines.slice(defIndex + 1).join('\n');
    if (new RegExp(`\\b${fn}\\s*\\(`).test(body)) recursiveFns.push(fn);
  });
  recursiveFns.forEach((fn) => influential.push(`Recursion: ${fn}()`));

  // --- binary search heuristic -------------------------------------------
  const isBinarySearch =
    maxLoopDepth >= 1 &&
    /mid/.test(code) &&
    (/\/\/\s*2/.test(code) || /\/\s*2/.test(code)) &&
    (/low/.test(code) || /left/.test(code)) &&
    (/high/.test(code) || /right/.test(code));

  // --- sorting heuristic ---------------------------------------------------
  const hasSort = /\b(sorted\s*\(|\.sort\s*\()/.test(code);

  // --- time classification -------------------------------------------------
  let timeBigO = 'O(1)';
  if (recursiveFns.length > 0 && maxLoopDepth === 0) {
    timeBigO = 'O(n) (recursive; exact branching not determined)';
    assumptions.push('Recursion depth is assumed linear in input size; branching factor could not be determined exactly.');
  } else if (isBinarySearch) {
    timeBigO = 'O(log n)';
  } else if (maxLoopDepth >= 2) {
    timeBigO = `O(n^${maxLoopDepth})`;
  } else if (maxLoopDepth === 1) {
    timeBigO = 'O(n)';
  } else if (hasSort) {
    timeBigO = 'O(n log n)';
  }

  if (hasSort && maxLoopDepth < 2 && !isBinarySearch) {
    // sorting dominates a single linear pass
    if (timeBigO === 'O(n)' || timeBigO === 'O(1)') timeBigO = 'O(n log n)';
  }

  let timeExplanation = '';
  if (maxLoopDepth === 0 && recursiveFns.length === 0) {
    timeExplanation = 'No loops or recursion detected; work is bounded by a fixed number of operations.';
  } else if (isBinarySearch) {
    timeExplanation = 'A loop halves the search range each iteration (mid calculation), giving logarithmic time.';
  } else if (maxLoopDepth >= 2) {
    timeExplanation = `${maxLoopDepth} nested loop level(s) detected; each iterates over the input, giving polynomial time.`;
  } else if (maxLoopDepth === 1) {
    timeExplanation = 'A single loop iterates over the input once.';
  } else if (recursiveFns.length > 0) {
    timeExplanation = 'Recursion detected; complexity depends on branching and depth (see assumptions).';
  } else if (hasSort) {
    timeExplanation = 'Sorting operation detected, which is typically O(n log n).';
  }

  const timeBest = timeBigO.startsWith('O(n^2)') ? 'O(n)' : timeBigO === 'O(n log n)' ? 'O(n log n)' : timeBigO;
  const timeWorst = timeBigO;

  // --- space classification -----------------------------------------------
  const spaceInfluential: string[] = [];
  const spaceAssumptions: string[] = [
    'Input storage is excluded; only auxiliary/extra memory is counted.',
  ];
  let spaceBigO = 'O(1)';
  // recursion stack
  if (recursiveFns.length > 0) {
    spaceBigO = 'O(n)';
    spaceInfluential.push(...recursiveFns.map((f) => `Recursive call stack: ${f}()`));
    spaceAssumptions.push('Recursion depth assumed linear in input size.');
  }
  // array/list/dict allocations, especially inside loops or of size n
  lines.forEach((raw, i) => {
    const line = raw.trim();
    if (/\b(list|dict|set)\s*\(/.test(line) || /\[\s*\]/.test(line) || /\.append\s*\(/.test(line)) {
      // heuristic: allocation inside a loop -> O(n); top-level fixed -> O(1)
      if (/\.append\s*\(/.test(line) || /\[\s*[^\]]*for\s+/.test(line)) {
        if (spaceBigO !== 'O(n)') spaceBigO = 'O(n)';
        spaceInfluential.push(`Line ${i + 1}: grows a collection (${line.slice(0, 60)})`);
      }
    }
  });
  if (spaceInfluential.length === 0) {
    spaceInfluential.push('No growing data structures detected; only a fixed number of variables.');
  }
  if (spaceBigO === 'O(1)') {
    spaceAssumptions.push('No auxiliary arrays/lists/maps of input size were detected.');
  }

  return {
    time: {
      bigO: timeBigO,
      best: timeBest,
      average: timeBigO,
      worst: timeWorst,
      explanation: timeExplanation,
      influential: influential.length ? influential : ['No dominant operations detected.'],
      assumptions,
    },
    space: {
      bigO: spaceBigO,
      explanation:
        spaceBigO === 'O(1)'
          ? 'Only a fixed number of variables are used; no input-sized auxiliary storage detected.'
          : 'Auxiliary storage grows with input size (collections and/or recursion stack).',
      influential: spaceInfluential,
      assumptions: spaceAssumptions,
    },
  };
}
